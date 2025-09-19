# 📝 MVT 3 Grammar Specification

---

## 1. Lexical Elements (Tokens)

### Identifiers

```
IDENTIFIER ::= [A-Za-z_][A-Za-z0-9_]*
```

### Literals

```
INT_LITERAL       ::= [0-9ab]+          ; base-12 dodecagram literal
FLOAT_LITERAL     ::= [0-9ab]+ '.' [0-9ab]+
STRING_LITERAL    ::= '"' .*? '"'       ; double-quoted strings
BOOL_LITERAL      ::= "true" | "false"
```

### Keywords (Reserved)

```
; Trizzle Core
MAIN       PROG       END       RUN
LET        PRINT      DISPLAY
IF         ELSE       ELSEIF    SWITCH   BRANCH
LOOP       FROM       TO
ASYNC      AWAIT      ROUTINE   JOIN     MUTEX
TRY        CATCH      THROW

; Veil Core
TASK       INTENTION  TOOL      LOGIC
RETURN     GET        SET

; Shared
MODULE     IMPORT     EXPORT
STRUCT     TUPLE      LIST      VECTOR   ARRAY
```

### Operators

```
PLUS       ::= "+"
MINUS      ::= "-"
MUL        ::= "*"
DIV        ::= "/"
ASSIGN     ::= "="
EQ         ::= "=="
NEQ        ::= "!="
LT         ::= "<"
GT         ::= ">"
LEQ        ::= "<="
GEQ        ::= ">="
ARROW      ::= "->"
```

### Punctuation

```
LPAREN     ::= "("
RPAREN     ::= ")"
LBRACE     ::= "{"
RBRACE     ::= "}"
LBRACK     ::= "["
RBRACK     ::= "]"
COLON      ::= ":"
SEMICOLON  ::= ";"
COMMA      ::= ","
```

### Comments

```
COMMENT    ::= ";" .*    ; single-line comment
```

---

## 2. Grammar (BNF)

### Program

```
<program> ::= <trizzle_program> | <veil_program>
```

---

### Trizzle Mode

```
<trizzle_program> ::= ("Main" | "Prog") "(" ")" <block> ("end" | "run")

<block> ::= "{" { <statement> } "}"

<statement> ::= <declaration>
               | <assignment>
               | <print_stmt>
               | <if_stmt>
               | <loop_stmt>
               | <async_stmt>
               | <try_catch_stmt>
               | <expr> ";"

<declaration> ::= "let" IDENTIFIER "=" <expr>

<assignment> ::= IDENTIFIER "=" <expr>

<print_stmt> ::= "Print" "[" STRING_LITERAL "]"
               | "Display" "[" STRING_LITERAL "]"

<if_stmt> ::= "if" <expr> <block> { "elseif" <expr> <block> } [ "else" <block> ]

<loop_stmt> ::= "loop" "(" IDENTIFIER "from" <expr> "to" <expr> ")" <block>

<async_stmt> ::= "async" "routine" <block>
<await_stmt> ::= "await" IDENTIFIER

<try_catch_stmt> ::= "try" <block> "catch" <block>

<expr> ::= <term> { ("+" | "-") <term> }
<term> ::= <factor> { ("*" | "/") <factor> }
<factor> ::= INT_LITERAL | FLOAT_LITERAL | STRING_LITERAL | BOOL_LITERAL | IDENTIFIER | "(" <expr> ")"
```

---

### Veil Mode

```
<veil_program> ::= "Task" "{" <intention_decl> <tool_decl> <logic_decl> "}"

<intention_decl> ::= "Intention:" IDENTIFIER [ "(" <param_list> ")" ] ";"
<tool_decl>      ::= "Tool:" IDENTIFIER ";"
<logic_decl>     ::= "Logic:" "{" { <logic_stmt> } "};"

<param_list> ::= <param> { "," <param> }
<param>      ::= <type> IDENTIFIER

<type> ::= "Int" | "Float" | "Bool" | "String"

<logic_stmt> ::= "Return:" <expr> ";"
               | "Print:" STRING_LITERAL ";"
               | "Get:" IDENTIFIER ";"
               | "Set:" IDENTIFIER "=" <expr> ";"
               | <trizzle_stmt_in_logic>

<trizzle_stmt_in_logic> ::= <declaration> | <assignment> | <if_stmt> | <loop_stmt>
```

---

## 3. Notes on Unification

* **Trizzle mode** = explicit execution blocks (`Main`, `Prog`).
* **Veil mode** = declarative tasks (`Task { Intention … Tool … Logic … }`).
* Both compile into the **same AST nodes** (functions, calls, blocks).
* **Dodecagram literals**: must be converted at lexer stage into decimal equivalents before IR.
* **Macros (CIAMS)** will be handled at preprocessing step before parsing.

---

## 4. AST Node Mapping

| Node Type     | Source Form            | Target IR               |
| ------------- | ---------------------- | ----------------------- |
| Main/Prog     | `Main () { … }`        | entrypoint function     |
| Task          | `Task { … }`           | function with metadata  |
| Intention     | `Intention: name()`    | function signature      |
| Tool          | `Tool: console;`       | annotation / capability |
| Logic         | `Logic { … }`          | function body           |
| Print/Display | `Print ["msg"]`        | call to runtime print   |
| Loop          | `loop (i from a to b)` | for/while loop IR       |
| If/Else       | standard conditional   | branch IR               |
| Async/Await   | `async … await …`      | coroutine/fiber wrapper |

---

✅ This BNF + token spec is **ready to drive a lexer/parser generator** (ANTLR, hand-rolled, or recursive descent).
From here, we can build the **AST classes** and a **codegen skeleton** (LLVM IR → WASM/.exe).

---

Would you like me to **write the AST class hierarchy in Python** (nodes, visitors, codegen hooks) next, so you can immediately start building the compiler backend?
