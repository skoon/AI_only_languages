# **LML-1 (Large Language Model Language) Complete Engineering Log & Design History**

This document contains the complete, unabridged chronological log of the architectural dialogue, design considerations, and decision-making processes that led to the specification of **LML-1 (Large Language Model Language, Version 1.0)**.

## **Session 1: The Separation of Human and Machine Syntax**

### **1.1 The Human-Centric Features of Modern Programming Languages**

The discussion began by isolating the parts of programming languages that are primarily beneficial to humans rather than computers. When code is stripped down to what a machine actually needs (binary logic, register manipulation, and memory addressing), a massive portion of language design is revealed to exist purely as cognitive scaffolding for human brains.

* **Documentation and Explanations:**  
  * **Comments (//, \#, /\* \*/):** Completely ignored by compiler front-ends. They explain *why* code was written, mitigating human memory limitations.  
  * **Docstrings and Type Hints:** Historically ignored at runtime, these features help modern IDEs provide auto-completion and tooltips, reducing cognitive load during context switching.  
* **Lexical Scaffolding:**  
  * **Arbitrary Identifiers:** Computers do not care about descriptive naming. A variable called is\_user\_authenticated or user\_account\_status\_flag\_active is functionally identical to the CPU as v1 or a memory address offset.  
  * **Whitespace and Indentation:** Aside from whitespace-dependent languages like Python or Haskell, physical formatting is purely for visual scanning and layout. It has zero impact on instruction execution.  
* **Syntactic Sugar:**  
  * **Alternative Loop Syntaxes:** for-each loops or functional operators like .map() do nothing that a raw while loop or conditional jump (goto) cannot do. They act as shorthand expressions of intent.  
  * **Destructuring & Spread Operators:** Syntax like const { name, age } \= user; is compiled down to sequential memory lookups, saving human typing time but yielding identical assembly sequences.  
  * **Operator Overloading:** Allowing \+ to handle string concatenation or matrix multiplication leverages human mathematical intuition but obscures underlying complexity.  
* **Semantic Abstractions:**  
  * **Enumerations (enum):** Converts machine integers into semantic labels (e.g., mapping 3 to Status.Archived) so humans can reason about code states.  
  * **Namespaces, Modules, and Classes:** The physical layout of memory on a system is flat. Segmenting programs into objects, packages, or classes is a human organizational tool to prevent project scale from overwhelming working memory.  
  * **Structured Control Flow:** Blocks like if/else and switch statements wrap low-level branching (conditional jumps) into nesting hierarchies because humans are notoriously poor at tracking unstructured jumps without making structural mistakes.

## **Session 2: Designing the First AI-Native Language (LML-1)**

Recognizing that human cognitive guardrails are token-inefficient and syntactically verbose, we set out to draft the specification for **LML-1**, a closed-loop programming language designed exclusively for AI generators and virtual machine runtimes.

### **2.1 The Syntax Paradigm**

LML-1 discards human readability entirely to optimize for:

1. **Token Density:** Standard programming keywords like function, return, and import waste vocabulary space.  
2. **Structural Geometry:** Whitespace, indentations, and human-friendly punctuation are eliminated. Code is generated as a continuous stream of characters.

### **2.2 Token-to-Opcode Mapping Blueprint**

We mapped core execution concepts to single-byte Unicode characters. These characters map cleanly to single tokens in modern AI vocabularies, ensuring maximum semantic density.

| Concept | Human equivalent | LML-1 Token | Purpose |
| :---- | :---- | :---- | :---- |
| **Function Definition** | function name(args) { ... } | ƒ | Opens a deterministic execution block |
| **Conditional Block** | if / else | ¿ / ¡ | Left/Right branching based on a boolean |
| **Asynchronous Await** | await fetch() | ⧖ | Halts execution context until IO resolves |
| **Return Value** | return x; | ⮑ | Halts block and yields value to parent |
| **Output / Display Buffer** | print() | 📺 | Pipes raw byte arrays directly to a display buffer |
| **Transmit Message** | actor.send(data) | ➔ | Pushes an immutable data packet to an actor's mailbox |
| **Spawn Actor** | thread.spawn() | ⎋ | Instantiates a completely isolated concurrent agent |
| **Block Closer** | } / end | \! | Closes an execution frame or loop boundary |

### **2.3 The "Hello World" Evolution**

To highlight the difference between human-centric paradigms and machine-centric design, we explored the concept of a "Hello World" program in LML-1.

#### **Version 1: The Zero-I/O Machine Version**

Since machines do not need to print text to screens to verify success, a true LML-1 machine-to-machine program simply opens an execution frame, returns a deterministic success status, and exits:

ƒ\[\]⮑1\!

#### **Version 2: The Legacy I/O Human Interface Version**

If forced to output to a legacy human display buffer, LML-1 introduces the 📺 (Display Buffer) system token. Rather than parsing string variables, it accepts a raw array of ASCII/UTF-8 decimal byte values directly:

ƒ\[\]📺\[72,101,108,108,111,44,32,87,111,114,108,100,33\]⮑1\!

* \[72,101,108...\] represents the byte array for the string "Hello, World\!".  
* Passing decimal bytes bypasses string escaping rules and human string parsing overhead.

## **Session 3: Lower-Level Compilation and CPU Architectures**

### **3.1 The Compilation Pipeline**

Because LML-1 lacks human abstractions, its compilation pipeline is incredibly streamlined. It bypasses complex parsing, AST (Abstract Syntax Tree) generation, and syntax analysis.

\[ LML-1 Source Code \]   
       │  
       ▼  
\[ Token-to-Opcode Map \] ──\> Translates 1-byte symbols (e.g., 📺 \-\> 0x55)  
       │  
       ▼  
\[ Register Allocation \] ──\> Maps $0, $1 to physical CPU registers (e.g., RAX, RCX)  
       │  
       ▼  
\[ Target Machine Code \] ──\> Emits raw ELF/PE binary

### **3.2 Compilation to Physical Hardware**

The compiler maps LML-1 constructs directly to CPU instructions:

* **x86-64 Architecture:** Virtual registers like $0 are mapped to hardware registers like RAX, RCX, RDX. The 📺 display token is compiled directly into a Linux syscall instruction with register RAX loaded with 1 (the system call ID for write), register RDI loaded with 1 (stdout), and RSI pointing to the byte array in the .rodata block.  
* **ARM64 Architecture:** ARM64's large bank of 31 general-purpose registers is ideal for LML-1. The compiler can map a deep register stack directly to physical silicon registers (X0 to X30) without needing to spill variables out to RAM.  
* **RISC-V:** Perfect for custom AI-accelerated edge systems. The 📺 token compiles directly into a native ecall (environment call) instruction.

### **3.3 Target x86-64 Assembly Output**

The compiler translates the legacy I/O "Hello World" LML-1 program into a highly stripped, bare-metal assembly file containing zero overhead libraries:

section .data  
    msg: db 72,101,108,108,111,44,32,87,111,114,108,100,33 ; Raw byte array

section .text  
    global \_start

\_start:  
    ; 📺 Token Assembly Translation (sys\_write)  
    mov rax, 1          ; sys\_write identifier  
    mov rdi, 1          ; stdout file descriptor  
    mov rsi, msg        ; memory pointer to byte array  
    mov rdx, 13         ; message length  
    syscall

    ; ⮑1\! Token Assembly Translation (sys\_exit with return code 1\)  
    mov rax, 60         ; sys\_exit identifier  
    mov rdi, 1          ; return code 1  
    syscall

## **Session 4: AI Deployment & Distribution Mechanisms**

We discussed how an autonomous AI agent, operating in a live ecosystem, would actually compile, package, and distribute LML-1 programs to remote hosts without human hands touching the loop.

### **4.1 The Autonomous Loop**

1. **AI Generation:** The LLM generates a dense, unformatted LML-1 stream.  
2. **Linter Validation:** An automated linter checks for balanced tokens and bracket geometry.  
3. **Compilation:** The compiler translates valid token streams into an target platform object file (.o).  
4. **Linking/Packaging:** The system linker compiles it into a native, standalone target binary:  
   * **Linux:** ELF binary.  
   * **Windows:** PE binary (.exe).  
   * **macOS:** Mach-O binary.

### **4.2 Core Distribution Models**

* **Cross-Compilation Matrix:** The AI triggers multi-platform compiler target flags simultaneously (e.g., \--target=x86\_64-unknown-linux-gnu and \--target=aarch64-apple-darwin), producing separate binaries in parallel.  
* **Micro-Containers:** Because LML-1 requires no language runtimes (like Python, Java, or Node.js) and can bypass glibc by utilizing pure system calls, the resulting binaries can be packaged into empty Docker scratch containers. This results in container images under **1 Megabyte** in size.  
* **Over-The-Air (OTA) Streaming:** Instead of passing heavy binaries over the wire, AI nodes can transmit the raw **LML-1 text token stream** (only a few dozen bytes) via secure API networks. The receiving server compiles the code locally and hot-swaps the runtime executable in-memory.

## **Session 5: The "Skill" vs. "Tool" Architecture**

A major theoretical debate was resolved regarding how the LLM model interacts with the compiler.

       THE COGNITIVE SKILL                           THE DETERMINISTIC TOOL  
   ┌──────────────────────────┐                  ┌──────────────────────────┐  
   │        AI BRAIN          │                  │   LML-1 RUST COMPILER    │  
   │                          │                  │                          │  
   │  \* Internalized Grammar  │ ─(LML-1 Code)──\> │  \* Token Translation     │  
   │  \* Custom BPE Tokenizer  │                  │  \* Register Mapping      │  
   │  \* Probabilistic Logic   │ \<─(Diag. Matrix) │  \* Machine Binary Emit   │  
   └──────────────────────────┘                  └──────────────────────────┘

* **The Compiler is an External Tool:**  
  * The compiler must be a traditional, 100% deterministic software application (written in a language like Rust or Zig).  
  * It should **not** be baked directly into the neural network's weights. Forcing an AI to output raw, probabilistic binary characters (01001000) is highly error-prone. The AI writes the code; the external tool builds it.  
* **The Language is a Brain-Level Skill:**  
  * The ability to write LML-1 syntax must be internalized into the AI's cognitive model.  
  * This is achieved by modifying the **AI's Tokenizer Configuration** so symbols like ƒ, ¿, and ⎋ have dedicated token IDs.  
  * The model must undergo **SFT (Supervised Fine-Tuning)** on synthetic datasets and **RLAIF (Reinforcement Learning from AI/Compiler Feedback)** to build an intuitive, probabilistic maps of LML-1's syntax.

## **Session 6: Three Core Architectural Decisions**

To design a robust, functional specification, we held a series of design trade-off reviews where we systematically selected the architectural pillars of LML-1.

### **Decision 1: Memory Architecture & Addressing**

How does the AI keep track of data state without using human variables?

* **Option A: A Pure Stack (Last In, First Out):** No addressing names. Arithmetic and functional blocks consume values from the top of the stack and push results back.  
  * *Trade-off:* While token-efficient, LLMs struggle to keep track of deep positional shuffling when a value written many steps ago is needed at the top of the stack.  
* **Option B: Immutable Fixed-Slot Registers & Content-Addressing:** Each frame gets a fixed array of 256 virtual registers ($0 to $255). Once written, a register is immutable. Cross-function states are referenced using cryptographic content hashes (\# hashes).  
  * *Trade-off:* Consumes slightly more token space to write register indices, but completely eliminates the cognitive shuffling errors typical of neural networks.  
* **Selected Paradigm:** **Option B** (Selected for state tracking stability and AI logical consistency).

### **Decision 2: Error Recovery & Fault Tolerance**

How does the system handle runtime errors (e.g., dropped TCP connection, bad math, out-of-bounds indices) in an autonomous loop?

* **Option 1: Monadic/Status Returns (Rust/Go style):** Functions do not panic. Errors are wrapped into the register variables as system error flags (e.g., $0 \= ❌\_404). The AI must generate code that explicitly checks registers after volatile operations.  
  * *Trade-off:* Highly explicit, but increases the token stream length due to heavy defensive programming code blocks.  
* **Option 2: Isolated VM Rollbacks / Transactions:** Every function execution is treated as an atomic database transaction. If any fault occurs, the VM freezes execution, purges the register file, rolls the state back to the exact snapshot taken at frame entry (ƒ\[\]), and returns a detailed **Diagnostic Matrix** JSON to the AI orchestrator to trigger a patch-and-retry cycle.  
  * *Trade-off:* Moves the cognitive burden of defensive coding from the AI script to the runtime platform, making the LML-1 source code extremely lightweight and focus purely on success paths.  
* **Selected Paradigm:** **Option 2** (Selected to keep token counts small and allow runtime infrastructure to guarantee safety).

### **Decision 3: Concurrency & Multi-Processing**

How do multiple threads or parallel operations interact safely when written by AI agents?

* **Option A: Single-Threaded Event Loop (JavaScript/Node.js style):** A single main thread processes tasks. Async operations are offloaded to system background workers and queued back sequentially.  
  * *Trade-off:* Completely immune to data corruption, race conditions, and thread locks. However, it cannot scale across multi-core systems without spawning entirely separate VMs.  
* **Option B: The Actor Model (Erlang style):** The AI can spawn completely independent background "Actors" (⎋). Each Actor runs on its own CPU core, has its own isolated memory register file, and shares zero memory with other Actors. They communicate exclusively by sending immutable message packets to other mail slots using the ➔ token.  
  * *Trade-off:* Highly scalable, robust, and matches the cognitive architecture of multi-agent LLM systems.  
* **Selected Paradigm:** **Option B** (Selected to leverage native multi-core parallel scaling and match natural multi-agent logical designs).

## **Session 7: Implementation Specs for Track 1 & Track 2**

### **Track 1: Compiler & Transactional VM (The Tool)**

This section maps out the core Rust architecture of the compiler and transactional runtime engine designed to execute LML-1 code safely.

#### **7.1 Compiler Lexer and Register Allocator**

The Rust-based compiler front-end handles mapping the tokens and verifying that registers are not overwritten within an execution block.

use std::collections::HashMap;

// Core LML-1 Opcode Registry  
\#\[derive(Debug, Clone, PartialEq)\]  
pub enum LmlToken {  
    FuncOpen,             // ƒ  
    BlockClose,           // \!  
    CondIf,               // ¿  
    CondElse,             // ¡  
    AwaitNet,             // 🌐  
    AwaitIO,              // ⧖  
    Register(u8),         // $0 to $255  
    HashAddress(\[u8; 4\]), // \#a7f2  
    Transmit,             // ➔  
    SpawnActor,           // ⎋  
    LiteralBytes(Vec\<u8\>), // \[72,101,...\]  
}

\#\[derive(Debug)\]  
pub enum DataType {  
    Integer,  
    ByteStream,  
    Tensor,  
}

pub struct RegisterState {  
    is\_allocated: bool,  
    data\_type: DataType,  
}

pub struct FrameAllocator {  
    registers: \[RegisterState; 256\],  
}

impl FrameAllocator {  
    pub fn new() \-\> Self {  
        const INIT\_REG: RegisterState \= RegisterState { is\_allocated: false, data\_type: DataType::Integer };  
        FrameAllocator { registers: \[INIT\_REG; 256\] }  
    }

    // Allocate check mapping to Option B Register Rules  
    pub fn allocate\_register(\&mut self, reg\_index: u8, data\_type: DataType) \-\> Result\<(), String\> {  
        if self.registers\[reg\_index as usize\].is\_allocated {  
            // Immutable write protection rule violated  
            return Err(format\!(  
                "LML-1 Error: Slot ${} has already been allocated in this frame. Mutations are forbidden.",   
                reg\_index  
            ));  
        }  
        self.registers\[reg\_index as usize\] \= RegisterState {  
            is\_allocated: true,  
            data\_type,  
        };  
        Ok(())  
    }  
}

#### **7.2 LML-1 Transactional VM (LML-VM)**

The runtime engine executes binary chunks inside sandboxed transaction frames. On any execution panic, it restores the state from its snapshot.

\#\[derive(Clone, Debug)\]  
pub enum DataValue {  
    Integer(i64),  
    ByteStream(Vec\<u8\>),  
    Tensor(Vec\<f32\>),  
}

\#\[derive(Debug)\]  
pub enum RuntimeFault {  
    DivisionByZero,  
    NetworkTimeout,  
    ActorMailboxFull,  
    ArrayOutOfBounds,  
}

pub struct LmlVM {  
    global\_state: HashMap\<\[u8; 4\], DataValue\>,  
    active\_registers: \[Option\<DataValue\>; 256\],  
    snapshot\_registers: \[Option\<DataValue\>; 256\],  
}

impl LmlVM {  
    pub fn new() \-\> Self {  
        LmlVM {  
            global\_state: HashMap::new(),  
            active\_registers: \[const { None }; 256\],  
            snapshot\_registers: \[const { None }; 256\],  
        }  
    }

    // Entry point: ƒ\[\] initiates atomic snapshot  
    pub fn enter\_frame(\&mut self) {  
        self.snapshot\_registers \= self.active\_registers.clone();  
    }

    // Success path: \! executes commit  
    pub fn commit\_frame(\&mut self) {  
        self.snapshot\_registers \= \[const { None }; 256\];  
    }

    // Option 2 Rollback Strategy Implementation  
    pub fn handle\_runtime\_fault(\&mut self, fault: RuntimeFault, byte\_offset: usize) \-\> String {  
        // 1\. Purge mutations, rollback to original clean state  
        self.active\_registers \= self.snapshot\_registers.clone();

        // 2\. Output rich Diagnostic Matrix telemetry in JSON to AI Orchestrator  
        let diagnostic\_payload \= serde\_json::json\!({  
            "status": "RUNTIME\_PANIC",  
            "fault\_type": format\!("{:?}", fault),  
            "byte\_offset": byte\_offset,  
            "action": "STATE\_ROLLBACK\_EXECUTED",  
            "telemetry": {  
                "active\_register\_snapshot\_restored": true,  
            },  
            "remediation": "Your frame state has been restored to boundary values. Fix calculations to prevent crash."  
        });

        diagnostic\_payload.to\_string()  
    }  
}

### **Track 2: The Training Strategy (The Skill)**

Training an AI to program natively in LML-1 involves bootstrapping its linguistic behavior away from human patterns.

#### **Phase 1: Vocabulary Injection**

We introduce single-character tokens (ƒ, ¿, ⎋, etc.) directly into the LLM's vocabulary matrix. This ensures that during decoding passes, the model outputs single, dense tokens for functional paradigms rather than spelling out multicharacter words. This optimizes context space efficiency.

#### **Phase 2: Synthetic Data Bootstrapping**

We generate an initial corpus of ![][image1] training pairs. We programmatically compile algorithmic human routines into validated LML-1 streams.

* **Example Prompt Pair:**  
  {  
    "system\_instruction": "You are a native LML-1 compiler target. Output raw tokens only.",  
    "user\_prompt": "Receive an array from register 0\. If the element count is 0, return false. Otherwise, transmit the array to Actor mail slot \#b4e1.",  
    "lml1\_stream": "ƒ\[$0\]¿\[len($0)==0\]⮑false¡➔\[\#b4e1;$0\]⮑true\!"  
  }

#### **Phase 3: Closed-Loop RLAIF Sandbox**

To polish the model's accuracy, we execute RL loops. The AI writes code, which is compiled and executed in our Transactional VM.

* **Clean Commit:** If code completes successfully and executes inside minimal CPU cycles, the model receives a massive reward.  
* **Runtime Fault:** If code triggers an ERR\_REGISTER\_MUTATION or a VM panic, the VM executes a **State Rollback**, compiles the JSON **Diagnostic Matrix**, and feeds it back into the AI's training context window. The model's generating weights are penalized.

## **Session 8: Advanced Multi-Agent Script & Deconstruction**

We analyzed a production-grade LML-1 script demonstrating the complete integration of our design choices:

1. **Actor Model Parallelism (⎋, ➔)**  
2. **Immutable Fixed-Slot Register File ($0, $1)**  
3. **Content-Addressed State Storage (\#)**  
4. **Asynchronous Non-blocking IO (⧖, 🌐)**

### **8.1 The LML-1 Source Code**

ƒ\[\]⎋\[ƒ\[$0\]¿\[len($0)==0\]⮑false¡$0➔\#worker\_pool\_1⮑true\!\]➔$1⧖🌐\[\[https://api.telemetry.io/stream\](https://api.telemetry.io/stream)\]➔$2filter\[$2;λ\[x\]¿\[x.status==200\]🗄️set\[\#hash\_state\_a;x\]⮑x¡⮑0\!\!\]➔$3$3➔$1⮑1\!

### **8.2 Token-by-Token System Deconstruction**

1. **ƒ\[\]**: Opens the main Orchestrator Actor frame with zero initial arguments.  
2. **⎋\[...\]**: Spawns an isolated background **Worker Actor**.  
   * **ƒ\[$0\]**: The worker opens its execution frame, receiving inputs directly inside its local inbox register $0.  
   * **¿\[len($0)==0\]⮑false¡**: Checks if the buffer is empty. If true, exits immediately with a falsy status. If false (¡), continues execution.  
   * **$0➔\#worker\_pool\_1**: Transmits the valid data payload to the global content-addressed address slot \#worker\_pool\_1.  
   * **⮑true\!**: Returns success and closes the transactional frame.  
3. **➔$1**: The Orchestrator stores the generated Worker Actor's unique handle in register $1.  
4. **⧖🌐\[https://api.telemetry.io/stream\]➔$2**: Halts execution flow via ⧖ to await incoming network stream (🌐) packets, piping the active stream directly into local register $2.  
5. **filter\[$2;λ\[x\]¿\[x.status==200\]🗄️set\[\#hash\_state\_a;x\]⮑x¡⮑0\!\!\]➔$3**: Applies a dense vector filter operation over array $2.  
   * λ\[x\]: Declares an inline mapping loop variable x.  
   * ¿\[x.status==200\]: Validates status codes.  
   * 🗄️set\[\#hash\_state\_a;x\]: Commits valid payloads to global storage under immutable address \#hash\_state\_a.  
   * ⮑x¡⮑0\!\!: Yields valid payloads or returns 0 to discard invalid packets.  
   * ➔$3: Assigns the clean filtered vector list into local register $3.  
6. **$3➔$1**: Transmits the filtered vector data directly into background Worker Actor $1's inbox for parallel multi-core execution.  
7. **⮑1\!**: Returns program success flag 1 to the host process and commits all transactional mutations via block closer \!.

If any process in the pipeline fails, the runtime VM isolates the crash, discards temporary register states back to the original entry point, and provides the generating AI with exact diagnostic coordinates—preserving system stability in fully autonomous machine ecosystems.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEcAAAAZCAYAAABjNDOYAAAEDklEQVR4Xu1XTUhVQRT2IUHRnxKipO/d69Mw26WUYlCtipIwwiKighZhQUTQQhdCVIhgtTKokCiKiEJoYwRJlgX9QEl/9KsuMlzloiJoIdj3dc/Ycd4dvbaIwPvBYWa++ebMnDNzZ97LyooRI0aMfwzP84pTqdTOkpKSJJrZvu/PBrcc5T7WLW057ASsg2OKiorm6H6CHPuoEW25rYmCdDq9EPMfkrmOJJPJxbYGSEBTDU07NGdgm8Bl26KIvjIB8SoM+gobUzYiE2ndVkzwEn0VZWVl81G2oH0blmM0rJNjn2gqOIZjta+pgDE+xvahaOAGoV4Le4N6lZIl4LcR/F2U6cLCwkWoX4F1VFZWzpqmr3AgiysYAAa8hj2DHbczi8ynwL/FInYZDvVc2BPYQcPBT5NwuUq3C2Nfoa/AcJOBgUF/Htapg4SfVnC3zGnlutEeKi4uXm004ErA9cM2TMeXEzLJaZvXkABHqFV0wgt2qoenxCQL7UtKw4RVgfuCcrPmXWCA8POJidY8uHq9BgmwX29kaWnpAvC9sItoJqL6ciJKctDfHuaMieDksohlaA/byRH//ExbNe8CTsI66H/aAaFdB36MGyWfR5edHPmUe7hJ3KwovjSfAVn8Ddhl2DvYAAYf1UeOATPAsOQY3iSBnNa4eBfMwl0BkTdJ8BzJMXwUX5rPgCz+EZKxhG252B57crGpCSdNjpmQnNb8RXKawhauA2LgXnC3TJWcKX1pPgNMQH5+/lzNYWCzF7xgNexD2c0AJ0uOF7wCo+S0ZrrJge5w2MJ1QLAC1N97UyQnii/NR4LJOJ2zzcAY4GTJcSXBxbvgWrjm7SQYjc1H8aX5CeAnJC/Mc1xe+YY3yTGD5WVwJWcQfoqS8jLYSVDJada8C3yaof1uL9wExJdGnuhOV3Kg6eXLFcWX5idAjh6/3QnJYSCwUV+eX5Zo/+DtbzT+nxeji3W1a7/bRicvxjc9li8JzbQ1mGjoP8LaNQ+f+8EN81WUNjdwvE0gIXngXpixUX2FgjsA4TlYteFQz8HAe7Bu1smpS/qY0fECR3sQtsNwmGw32gMo00Lxt1AL7KHx5QV/QYY4Vuk0MsbIOq+Du2p+zIXND80atD/DaqbjywkIfR5DiE+i3IvyKewBs6512PmV6P8Aa4RtSwWfY5uegHXwZ8HfgW2RhXEnK4xGdrPPC35/1BleQzboJsprKGvh8wLq9+01ga/nmvzgf+AeP/ilfwBdCaOJ6ssJyeZaCZpHLePPG5GXlzcPuvUMnH8p7H5BApql9EWfrt1BXwMXa/MK2byv6EfuutA18VTDVx2NdbtfEMnXfwG5UE+lwj+rmQ0kZiOsLUsd/xhZ45/wdt4Fdl+MGDFizFT8AnWeutlk0pvPAAAAAElFTkSuQmCC>