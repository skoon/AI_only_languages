# Training an AI Model on AIRL

A complete guide to taking generated AIRL training data and producing a
fine-tuned model capable of emitting valid AIRL computation graphs.

---

## Overview

Each dataset entry produced by the AIRL generator contains four distinct
training signals:

| Signal | Input | Output | Purpose |
|---|---|---|---|
| Goal-to-graph | Intent graph | AIRL program | Primary: teach the model to emit valid AIRL |
| Validity classification | AIRL program | VALID / INVALID | Teach the model to recognize correctness |
| Error prediction | AIRL program | Verification report | Teach the model to reason about failure |
| Confidence calibration | Node + context | Confidence score | Teach the model to know what it doesn't know |

Most training focuses on goal-to-graph generation. The others are supplementary
objectives that improve the model's internal reasoning.

---

## Step 1 — Choose a Base Model

You do not train from scratch. You fine-tune a pre-existing language model. The
base model provides general language understanding and code reasoning;
fine-tuning teaches it AIRL specifically.

A code-focused base model transfers better than a general-purpose one because
AIRL graphs are closer to structured code than natural language.

| Model | Notes |
|---|---|
| Qwen 2.5 Coder (7B / 14B) | Best starting point; pre-trained heavily on structured code |
| DeepSeek Coder V2 | Excellent at graph-structured reasoning |
| Llama 3.1 / 3.3 (8B / 70B) | Open weights; strong code reasoning; fine-tunable on consumer hardware at 8B |
| Mistral / Mixtral | Strong at structured JSON output |
| Phi-4 | Small but capable; good for resource-constrained environments |

---

## Step 2 — Format the Data

Language models train on text sequences. The JSONL entries from the generator
must be converted into prompt-completion pairs before training.

### Install dependencies

```bash
pip install transformers datasets trl peft accelerate bitsandbytes
```

### Formatter script

```python
# format_dataset.py
import json
import random

def format_entry(entry: dict) -> dict:
    intent = entry["intent"]
    program = entry["program"]
    verification = entry["verification"]

    system = (
        "You are an AIRL code generator. Given a structured intent graph, "
        "emit a valid AIRL computation graph in JSON-LD format. "
        "Every node must have a UUID id, @type, valueType, and confidence. "
        "Every effect used must be declared. "
        "The graph must be acyclic and have a valid entry point."
    )

    user = json.dumps({
        "goal": intent["goal"],
        "decomposition": intent["decomposition"],
        "difficulty": intent["difficulty"],
    }, indent=2)

    if entry["label"] == "VALID":
        assistant = json.dumps(program, indent=2)
    else:
        # Invalid entries: show the error so the model learns what went wrong
        assistant = json.dumps({
            "error": entry["mutationDescription"],
            "verification": verification,
            "corrected_program": None,
        }, indent=2)

    return {
        "messages": [
            {"role": "system",   "content": system},
            {"role": "user",     "content": user},
            {"role": "assistant","content": assistant},
        ]
    }


# Load, shuffle, and split
with open("dataset.jsonl") as f:
    entries = [json.loads(l) for l in f]

random.shuffle(entries)
n = len(entries)
splits = {
    "train": entries[:int(n * 0.8)],
    "val":   entries[int(n * 0.8):int(n * 0.9)],
    "test":  entries[int(n * 0.9):],
}

for name, data in splits.items():
    with open(f"{name}.jsonl", "w") as f:
        for entry in data:
            f.write(json.dumps(format_entry(entry)) + "\n")

print(f"train={len(splits['train'])}  val={len(splits['val'])}  test={len(splits['test'])}")
```

---

## Step 3 — Choose a Fine-Tuning Method

| Method | Memory required | Quality | When to use |
|---|---|---|---|
| Full fine-tuning | 80 GB+ for 70B | Highest | Only practical at 7–8B on a single A100 |
| LoRA / QLoRA | 4–8× less | Very good | Recommended starting point |
| RLCF | Builds on SFT | Best | Second phase after supervised training converges |

**Start with QLoRA.** It is the right first step for most situations: it runs on
two A100s even at 70B, is well-supported by existing tooling, and produces
strong results.

---

## Step 4 — Run Supervised Fine-Tuning (QLoRA)

```python
# train.py
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig
import torch

MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"

# 4-bit quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

# LoRA adapter
lora_config = LoraConfig(
    r=64,
    lora_alpha=128,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Load formatted dataset
dataset = load_dataset("json", data_files={
    "train": "train.jsonl",
    "validation": "val.jsonl",
})

# Training config
training_args = SFTConfig(
    output_dir="./airl-model-sft",
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,   # effective batch size = 16
    learning_rate=2e-4,
    bf16=True,
    logging_steps=10,
    evaluation_strategy="steps",
    eval_steps=100,
    save_steps=200,
    warmup_ratio=0.05,
    lr_scheduler_type="cosine",
    max_seq_length=4096,             # AIRL graphs can be long
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
)

trainer.train()
trainer.save_model("./airl-model-sft-final")
```

### Key hyperparameters to tune

| Parameter | Starting value | Notes |
|---|---|---|
| `r` (LoRA rank) | 64 | Higher = more capacity, more memory. Try 32, 64, 128. |
| `learning_rate` | 2e-4 | Lower (1e-4) if loss is unstable; higher (3e-4) if convergence is slow |
| `num_train_epochs` | 3 | More epochs risk overfitting; watch validation loss |
| `max_seq_length` | 4096 | Complex AIRL graphs with many nodes can be long |
| `per_device_batch_size` | 2 | Increase if GPU memory allows; use gradient accumulation to compensate |

---

## Step 5 — How Much Data You Need

The generator runs at approximately 4,000 entries per second, so data
generation is not the bottleneck — compute time is.

| Training goal | Minimum | Recommended |
|---|---|---|
| Model learns the AIRL JSON schema | 1,000 | 5,000 |
| Consistent valid graph emission | 10,000 | 50,000 |
| All 23 templates, all difficulty levels | 50,000 | 200,000 |
| Confidence calibration | 100,000 | 500,000 |
| Production-quality after RLCF | 500,000+ | 2,000,000+ |

Generate what you need in advance:

```bash
# 200,000 entries: ~50 seconds to generate
python generate.py --count 200000 --output ./dataset --seed 42 --format jsonl split
```

---

## Step 6 — Evaluate the Trained Model

After training, measure whether the model actually learned to emit valid AIRL.
The primary metric is **valid emission rate**: the fraction of generated programs
that pass all verifier checks.

```python
# evaluate.py
import json
from airl_generator.verifier import Verifier
from airl_generator.graph import ComputationGraph, Node, Edge, NodeKind, EdgeKind
from airl_generator.types import T_UNIT, EffectType

verifier = Verifier()

def reconstruct_graph(program: dict) -> ComputationGraph:
    raw = program.get("graph", {})
    graph = ComputationGraph()
    for n in raw.get("nodes", []):
        node = Node(
            node_id=n["id"],
            kind=NodeKind(n["@type"]) if n["@type"] in [k.value for k in NodeKind]
                 else NodeKind.EXEC,
            value_type=T_UNIT,
            confidence=n.get("confidence", 1.0),
            literal_value=n.get("data"),
        )
        for e in n.get("effects", []):
            try:
                node.effects.append(EffectType(e))
            except ValueError:
                pass
        graph.nodes.append(node)
    for e in raw.get("edges", []):
        graph.edges.append(Edge(
            from_id=e["from"], to_id=e["to"],
            kind=EdgeKind(e.get("type", "DATA")),
            slot=e.get("slot"),
        ))
    graph.entry_id = raw.get("entry")
    return graph


def evaluate(model, tokenizer, test_entries, n=500):
    results = {"pass": 0, "warn": 0, "fail": 0, "parse_error": 0}

    for entry in test_entries[:n]:
        prompt = format_intent_prompt(entry["intent"])
        output = model.generate(prompt, max_new_tokens=2048)
        raw = tokenizer.decode(output[0])

        try:
            program = json.loads(extract_json(raw))
            graph = reconstruct_graph(program)
            report = verifier.verify(graph, program["id"])
            results[report.overall_status.value.lower()] += 1
        except (json.JSONDecodeError, KeyError):
            results["parse_error"] += 1

    total = sum(results.values())
    print(f"PASS        : {results['pass']/total:.1%}")
    print(f"WARN        : {results['warn']/total:.1%}")
    print(f"FAIL        : {results['fail']/total:.1%}")
    print(f"Parse error : {results['parse_error']/total:.1%}")
    return results
```

### What to expect at each stage

| Stage | Expected valid emission rate |
|---|---|
| Base model (no fine-tuning) | < 5% (doesn't know AIRL) |
| After SFT on 10,000 entries | 40–60% |
| After SFT on 100,000 entries | 65–80% |
| After RLCF phase | 85–95%+ |

---

## Step 7 — RLCF Phase (Reinforcement Learning from Compiler Feedback)

After supervised fine-tuning converges, run a second training phase where the
AIRL verifier replaces the human reward labeler. The model is rewarded for
emitting graphs that compile cleanly, not just graphs that look like the
training examples.

This is the key architectural insight of the AIRL training pipeline: the reward
signal is objective, automated, infinitely scalable, and perfectly consistent.

```python
# train_rlcf.py
import json
import torch
from trl import PPOTrainer, PPOConfig
from airl_generator.verifier import Verifier

verifier = Verifier()


def compute_reward(generated_json: str) -> float:
    """
    Reward function using the AIRL verifier as the oracle.
    Returns a float in approximately [-1.0, +1.2].
    """
    try:
        program = json.loads(generated_json)
        graph = reconstruct_graph(program)
        report = verifier.verify(graph, program["id"])

        status = report.overall_status.value

        if status == "PASS":
            # Bonus reward for well-calibrated confidence scores
            avg_conf = report.passes[-1].meta.get("averageConfidence", 0.5)
            return 1.0 + (avg_conf - 0.5) * 0.2

        elif status == "WARN":
            return 0.3

        else:  # FAIL
            # Partial credit: reward how many passes the graph did pass
            n_passes = len(report.passes)
            n_passed = sum(1 for p in report.passes if p.status.value == "PASS")
            return -1.0 + (n_passed / n_passes) * 0.5

    except Exception:
        return -1.0   # Unparseable output gets the minimum reward


# Load the SFT-trained model
model = load_sft_model("./airl-model-sft-final")
tokenizer = load_tokenizer("./airl-model-sft-final")

ppo_config = PPOConfig(
    learning_rate=1e-5,
    batch_size=16,
    mini_batch_size=4,
    gradient_accumulation_steps=4,
)
ppo_trainer = PPOTrainer(ppo_config, model, tokenizer=tokenizer)

# RLCF training loop: generate → verify → reward → update weights
for batch in intent_dataloader:
    prompts   = [format_intent_prompt(i) for i in batch]
    responses = ppo_trainer.generate(prompts, max_new_tokens=2048)
    rewards   = [torch.tensor(compute_reward(r)) for r in responses]
    ppo_trainer.step(prompts, responses, rewards)

ppo_trainer.save_pretrained("./airl-model-rlcf-final")
```

### Reward signal breakdown

| Outcome | Reward | Rationale |
|---|---|---|
| All passes pass + high confidence | +1.0 to +1.2 | Best possible output |
| All passes pass | +1.0 | Valid emission |
| Warnings only | +0.3 | Partially correct; still useful |
| Some passes fail | -0.5 to 0.0 | Partial credit for what passed |
| All passes fail | -1.0 | Invalid graph |
| Unparseable JSON | -1.0 | Output format failure |

---

## Step 8 — Multi-Agent Verification (Advanced)

The final training enhancement runs two model instances against each other:
one emitter and one independent verifier. The emitter is rewarded not just for
passing the compiler checks but for producing graphs the verifier cannot find
faults with.

This adversarial dynamic closes the remaining gap between supervised learning
and the kind of deep constraint-satisfaction behavior described in the intrinsic
layer design. It is the most complex phase to set up but produces the highest
quality results.

```python
# The verifier model is a fine-tuned classifier trained to find errors
# in emitter output. It is kept frozen during emitter training.

def compute_adversarial_reward(
    generated_json: str,
    verifier_model,
    compiler_verifier: Verifier,
) -> float:
    # Primary reward: compiler
    compiler_reward = compute_reward(generated_json)

    # Secondary reward: adversarial verifier model
    # Ask the verifier model: "does this graph have errors?"
    verifier_verdict = verifier_model.classify(generated_json)
    adversarial_bonus = 0.2 if verifier_verdict == "VALID" else -0.1

    return compiler_reward + adversarial_bonus
```

---

## The Complete Pipeline

```
airl_generator/
  generate.py
      │
      │  dataset.jsonl  (VALID + INVALID entries with verification reports)
      ▼
format_dataset.py
      │
      │  train.jsonl / val.jsonl / test.jsonl  (prompt-completion pairs)
      ▼
train.py  (SFT / QLoRA)
      │
      │  airl-model-sft/
      ▼
evaluate.py  ←──────────────────── verifier.py
      │
      │  valid emission rate (target: 65–80% before RLCF)
      ▼
train_rlcf.py  ←─────────────────── verifier.py  (reward signal)
      │
      │  airl-model-rlcf/
      ▼
evaluate.py  ←──────────────────── verifier.py
      │
      │  valid emission rate (target: 85–95%+)
      ▼
  Production model
```

The verifier inside the generator is the same component that provides rewards
in the RLCF phase. The infrastructure built to generate training data is the
same infrastructure used to train the model. Nothing needs to be rebuilt.

---

## Hardware Reference

| Setup | Model size | Method | Notes |
|---|---|---|---|
| 1× RTX 4090 (24 GB) | 7–8B | QLoRA | Good starting point |
| 1× A100 (80 GB) | 7–8B | Full fine-tune or QLoRA | Recommended for SFT |
| 2× A100 (80 GB) | 70B | QLoRA | Sufficient for SFT |
| 4× A100 (80 GB) | 70B | Full fine-tune | Preferred for production |
| 8× H100 (80 GB) | 70B | SFT + RLCF | Full pipeline at scale |

For the RLCF phase, budget roughly 2–3× the compute of the SFT phase,
since PPO requires running the model multiple times per batch.

---

## Troubleshooting

**Loss does not decrease after epoch 1**
Reduce the learning rate to 1e-4 or lower. The model may be overfitting to
the training format rather than learning the graph semantics.

**Valid emission rate is stuck below 40%**
The model is likely learning the JSON structure but not the graph constraints.
Add more difficulty-1 and difficulty-2 examples to the training set and ensure
negative examples are at most 20% of the training data during the first epoch.

**Model produces valid JSON but the verifier always fails on effect-audit**
The effect system is the most novel part of AIRL relative to any base model's
training data. Oversample templates that use effects (any template with
`IO_STDOUT`, `IO_FILE_READ`, etc.) and ensure the system prompt explicitly
states the effect declaration requirement.

**RLCF reward collapses to -1.0**
The SFT model is not yet good enough to be the starting point for RLCF.
Continue SFT until the supervised valid emission rate is at least 50% before
switching to the reinforcement phase.

**Out of memory during RLCF**
PPO keeps the reference model in memory alongside the active model. Use
gradient checkpointing and reduce `mini_batch_size` to 1 or 2.
