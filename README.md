An exploration of asking an AI powered by an LLM to design a programming language strictly for AI's.

I prompted the AI's to "Isolate the parts of most programming languages that are primarily beneficial to humans when they are writing code."
 then "Create a spec for a programming language that is beneficial for LLMs or AI assuming that humans will not be modifying or reading the code. It will only be read by a computer and AI."

 The goal here was to see what these LLM's would think a non-human programming language would look like and see if it would provide any benefits. 

 Caveat: I am not a language architect. I have never built a compiler or a spec for a language. But I thought this was an interesting idea.

 The most interesting part was that Claude said that it could just output assembly. Which makes sense, we have LLM's spitting out Python or JavaScript code that then needs to be compiled based on the assumption that the compiler will catch any errors made by the human typing the code. Claude decided to remove the human error from the equation.