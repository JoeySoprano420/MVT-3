#!/usr/bin/env python3
"""
codegen.py — DGM → LLVM IR → NASM Translator
Version: 1.0.0
"""

import sys
import json
import argparse

# ------------------------------
# Colorama check
# ------------------------------
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    sys.stderr.write(
        "Error: The 'colorama' package is required for colored output.\n"
        "Install it with: pip install colorama\n"
    )
    sys.exit(1)

# ------------------------------
# Semantic Version
# ------------------------------
CODEGEN_VERSION = (1, 0, 0)

def version_string():
    return f"{CODEGEN_VERSION[0]}.{CODEGEN_VERSION[1]}.{CODEGEN_VERSION[2]}"

# ------------------------------
# Opcode Table (DGM_TABLE)
# 144 entries (0x00 → 0xBB)
# Grouped, expanded, trailing commas
# ------------------------------

DGM_TABLE = {
    # ==========================
    # Memory Instructions
    # ==========================
    0x00: {
        "bin": ["10010000"],
        "hex": ["0x90"],
        "llvm": "nop",
        "nasm": "NOP",
    },
    0x01: {
        "bin": ["1000000111101100"],
        "hex": ["0x81EC"],
        "llvm": "alloca",
        "nasm": "SUB RSP, imm32",
    },
    0x02: {
        "bin": ["10001011"],
        "hex": ["0x8B"],
        "llvm": "load",
        "nasm": "MOV R64, [MEM]",
    },
    0x03: {
        "bin": ["10001001"],
        "hex": ["0x89"],
        "llvm": "store",
        "nasm": "MOV [MEM], R64",
    },
    0x04: {
        "bin": ["10001101"],
        "hex": ["0x8D"],
        "llvm": "getelementptr",
        "nasm": "LEA R64, [MEM]",
    },
    0x05: {
        "bin": ["01100110"],
        "hex": ["0x66"],
        "llvm": "bitcast",
        "nasm": "MOVQ REG, XMM",
    },
    0x06: {
        "bin": ["00001111", "10110110"],
        "hex": ["0x0FB6"],
        "llvm": "trunc",
        "nasm": "MOVZX/MOVSX (narrow int)",
    },
    0x07: {
        "bin": ["00001111", "10111110"],
        "hex": ["0x0FBE"],
        "llvm": "zext",
        "nasm": "MOVSX (sign extend)",
    },
    0x08: {
        "bin": ["11000111"],
        "hex": ["0xC7"],
        "llvm": "sext",
        "nasm": "MOV R/M32, imm32",
    },
    0x09: {
        "bin": ["10001011"],
        "hex": ["0x8B"],
        "llvm": "fload",
        "nasm": "FLD MEM",
    },
    0x0A: {
        "bin": ["11011001"],
        "hex": ["0xD9"],
        "llvm": "fstore",
        "nasm": "FSTP MEM",
    },

      # ==========================
    # Arithmetic Instructions
    # ==========================
    0x0B: {
        "bin": ["00000001"],
        "hex": ["0x01"],
        "llvm": "add",
        "nasm": "ADD R/M32, R32",
    },
    0x0C: {
        "bin": ["00000011"],
        "hex": ["0x03"],
        "llvm": "add",
        "nasm": "ADD R32, R/M32",
    },
    0x0D: {
        "bin": ["10000011"],
        "hex": ["0x83"],
        "llvm": "add",
        "nasm": "ADD R/M32, imm8",
    },
    0x0E: {
        "bin": ["10000001"],
        "hex": ["0x81"],
        "llvm": "add",
        "nasm": "ADD R/M32, imm32",
    },
    0x0F: {
        "bin": ["00101001"],
        "hex": ["0x29"],
        "llvm": "sub",
        "nasm": "SUB R/M32, R32",
    },
    0x10: {
        "bin": ["00101011"],
        "hex": ["0x2B"],
        "llvm": "sub",
        "nasm": "SUB R32, R/M32",
    },
    0x11: {
        "bin": ["10000011"],
        "hex": ["0x83"],
        "llvm": "sub",
        "nasm": "SUB R/M32, imm8",
    },
    0x12: {
        "bin": ["10000001"],
        "hex": ["0x81"],
        "llvm": "sub",
        "nasm": "SUB R/M32, imm32",
    },
    0x13: {
        "bin": ["00001001"],
        "hex": ["0x09"],
        "llvm": "mul",
        "nasm": "MUL R/M32",
    },
    0x14: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "imul",
        "nasm": "IMUL R/M32",
    },
    0x15: {
        "bin": ["01101001"],
        "hex": ["0x69"],
        "llvm": "imul",
        "nasm": "IMUL R32, R/M32, imm32",
    },
    0x16: {
        "bin": ["01101011"],
        "hex": ["0x6B"],
        "llvm": "imul",
        "nasm": "IMUL R32, R/M32, imm8",
    },
    0x17: {
        "bin": ["11110110"],
        "hex": ["0xF6"],
        "llvm": "div",
        "nasm": "DIV R/M8",
    },
    0x18: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "div",
        "nasm": "DIV R/M32",
    },
    0x19: {
        "bin": ["11110110"],
        "hex": ["0xF6"],
        "llvm": "idiv",
        "nasm": "IDIV R/M8",
    },
    0x1A: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "idiv",
        "nasm": "IDIV R/M32",
    },

      # ==========================
    # Logic Instructions
    # ==========================
    0x1B: {
        "bin": ["00100001"],
        "hex": ["0x21"],
        "llvm": "and",
        "nasm": "AND R/M32, R32",
    },
    0x1C: {
        "bin": ["00100011"],
        "hex": ["0x23"],
        "llvm": "and",
        "nasm": "AND R32, R/M32",
    },
    0x1D: {
        "bin": ["10000011"],
        "hex": ["0x83"],
        "llvm": "and",
        "nasm": "AND R/M32, imm8",
    },
    0x1E: {
        "bin": ["10000001"],
        "hex": ["0x81"],
        "llvm": "and",
        "nasm": "AND R/M32, imm32",
    },
    0x1F: {
        "bin": ["00001001"],
        "hex": ["0x09"],
        "llvm": "or",
        "nasm": "OR R/M32, R32",
    },
    0x20: {
        "bin": ["00001011"],
        "hex": ["0x0B"],
        "llvm": "or",
        "nasm": "OR R32, R/M32",
    },
    0x21: {
        "bin": ["10000011"],
        "hex": ["0x83"],
        "llvm": "or",
        "nasm": "OR R/M32, imm8",
    },
    0x22: {
        "bin": ["10000001"],
        "hex": ["0x81"],
        "llvm": "or",
        "nasm": "OR R/M32, imm32",
    },
    0x23: {
        "bin": ["00110001"],
        "hex": ["0x31"],
        "llvm": "xor",
        "nasm": "XOR R/M32, R32",
    },
    0x24: {
        "bin": ["00110011"],
        "hex": ["0x33"],
        "llvm": "xor",
        "nasm": "XOR R32, R/M32",
    },
    0x25: {
        "bin": ["10000011"],
        "hex": ["0x83"],
        "llvm": "xor",
        "nasm": "XOR R/M32, imm8",
    },
    0x26: {
        "bin": ["10000001"],
        "hex": ["0x81"],
        "llvm": "xor",
        "nasm": "XOR R/M32, imm32",
    },
    0x27: {
        "bin": ["11110110"],
        "hex": ["0xF6"],
        "llvm": "not",
        "nasm": "NOT R/M8",
    },
    0x28: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "not",
        "nasm": "NOT R/M32",
    },
    0x29: {
        "bin": ["11110110"],
        "hex": ["0xF6"],
        "llvm": "neg",
        "nasm": "NEG R/M8",
    },
    0x2A: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "neg",
        "nasm": "NEG R/M32",
    },
    0x2B: {
        "bin": ["11010000"],
        "hex": ["0xD0"],
        "llvm": "shl",
        "nasm": "SHL R/M8, 1",
    },
    0x2C: {
        "bin": ["11010011"],
        "hex": ["0xD3"],
        "llvm": "shr",
        "nasm": "SHR R/M32, CL",
    },
    0x2D: {
        "bin": ["11010011"],
        "hex": ["0xD3"],
        "llvm": "sar",
        "nasm": "SAR R/M32, CL",
    },

      # ==========================
    # Control Flow Instructions
    # ==========================
    0x2E: {
        "bin": ["11101011"],
        "hex": ["0xEB"],
        "llvm": "br",
        "nasm": "JMP rel8",
    },
    0x2F: {
        "bin": ["11101001"],
        "hex": ["0xE9"],
        "llvm": "br",
        "nasm": "JMP rel32",
    },
    0x30: {
        "bin": ["11111111"],
        "hex": ["0xFF"],
        "llvm": "br_indirect",
        "nasm": "JMP R/M32",
    },
    0x31: {
        "bin": ["11101000"],
        "hex": ["0xE8"],
        "llvm": "call",
        "nasm": "CALL rel32",
    },
    0x32: {
        "bin": ["11111111"],
        "hex": ["0xFF"],
        "llvm": "call_indirect",
        "nasm": "CALL R/M32",
    },
    0x33: {
        "bin": ["11001101"],
        "hex": ["0xCD"],
        "llvm": "invoke",
        "nasm": "INT imm8",
    },
    0x34: {
        "bin": ["11001100"],
        "hex": ["0xCC"],
        "llvm": "trap",
        "nasm": "INT3",
    },
    0x35: {
        "bin": ["11000011"],
        "hex": ["0xC3"],
        "llvm": "ret",
        "nasm": "RET",
    },
    0x36: {
        "bin": ["11000010"],
        "hex": ["0xC2"],
        "llvm": "ret",
        "nasm": "RET imm16",
    },
    0x37: {
        "bin": ["11100011"],
        "hex": ["0xE3"],
        "llvm": "br_cond",
        "nasm": "JCXZ rel8",
    },
    0x38: {
        "bin": ["01110100"],
        "hex": ["0x74"],
        "llvm": "br_eq",
        "nasm": "JE rel8",
    },
    0x39: {
        "bin": ["01111101"],
        "hex": ["0x7D"],
        "llvm": "br_ne",
        "nasm": "JNE rel8",
    },
    0x3A: {
        "bin": ["01111111"],
        "hex": ["0x7F"],
        "llvm": "br_gt",
        "nasm": "JG rel8",
    },
    0x3B: {
        "bin": ["01111100"],
        "hex": ["0x7C"],
        "llvm": "br_lt",
        "nasm": "JL rel8",
    },
    0x3C: {
        "bin": ["01111110"],
        "hex": ["0x7E"],
        "llvm": "br_le",
        "nasm": "JLE rel8",
    },
    0x3D: {
        "bin": ["01111101"],
        "hex": ["0x7D"],
        "llvm": "br_ge",
        "nasm": "JGE rel8",
    },
    0x3E: {
        "bin": ["01110001"],
        "hex": ["0x71"],
        "llvm": "br_overflow",
        "nasm": "JO rel8",
    },
    0x3F: {
        "bin": ["01110010"],
        "hex": ["0x72"],
        "llvm": "br_no_overflow",
        "nasm": "JNO rel8",
    },

      # ==========================
    # Terminators
    # ==========================
    0x40: {
        "bin": ["11110100"],
        "hex": ["0xF4"],
        "llvm": "hlt",
        "nasm": "HLT",
    },
    0x41: {
        "bin": ["11110101"],
        "hex": ["0xF5"],
        "llvm": "cmc",
        "nasm": "CMC",
    },
    0x42: {
        "bin": ["11111000"],
        "hex": ["0xF8"],
        "llvm": "clc",
        "nasm": "CLC",
    },
    0x43: {
        "bin": ["11111001"],
        "hex": ["0xF9"],
        "llvm": "stc",
        "nasm": "STC",
    },
    0x44: {
        "bin": ["11111010"],
        "hex": ["0xFA"],
        "llvm": "cli",
        "nasm": "CLI",
    },
    0x45: {
        "bin": ["11111011"],
        "hex": ["0xFB"],
        "llvm": "sti",
        "nasm": "STI",
    },
    0x46: {
        "bin": ["11111100"],
        "hex": ["0xFC"],
        "llvm": "cld",
        "nasm": "CLD",
    },
    0x47: {
        "bin": ["11111101"],
        "hex": ["0xFD"],
        "llvm": "std",
        "nasm": "STD",
    },
    0x48: {
        "bin": ["11001111"],
        "hex": ["0xCF"],
        "llvm": "iret",
        "nasm": "IRET",
    },
    0x49: {
        "bin": ["11100010"],
        "hex": ["0xE2"],
        "llvm": "loop",
        "nasm": "LOOP rel8",
    },
    0x4A: {
        "bin": ["11100001"],
        "hex": ["0xE1"],
        "llvm": "loope",
        "nasm": "LOOPE rel8",
    },
    0x4B: {
        "bin": ["11100000"],
        "hex": ["0xE0"],
        "llvm": "loopne",
        "nasm": "LOOPNE rel8",
    },
    0x4C: {
        "bin": ["11100100"],
        "hex": ["0xE4"],
        "llvm": "in",
        "nasm": "IN AL, imm8",
    },
    0x4D: {
        "bin": ["11100101"],
        "hex": ["0xE5"],
        "llvm": "in",
        "nasm": "IN EAX, imm8",
    },
    0x4E: {
        "bin": ["11101100"],
        "hex": ["0xEC"],
        "llvm": "in",
        "nasm": "IN AL, DX",
    },
    0x4F: {
        "bin": ["11101101"],
        "hex": ["0xED"],
        "llvm": "in",
        "nasm": "IN EAX, DX",
    },
    0x50: {
        "bin": ["11100110"],
        "hex": ["0xE6"],
        "llvm": "out",
        "nasm": "OUT imm8, AL",
    },
    0x51: {
        "bin": ["11100111"],
        "hex": ["0xE7"],
        "llvm": "out",
        "nasm": "OUT imm8, EAX",
    },
    0x52: {
        "bin": ["11101110"],
        "hex": ["0xEE"],
        "llvm": "out",
        "nasm": "OUT DX, AL",
    },
    0x53: {
        "bin": ["11101111"],
        "hex": ["0xEF"],
        "llvm": "out",
        "nasm": "OUT DX, EAX",
    },

      # ==========================
    # Language Ops
    # ==========================
    0x54: {
        "bin": ["10110000"],
        "hex": ["0xB0"],
        "llvm": "mov_imm",
        "nasm": "MOV AL, imm8",
    },
    0x55: {
        "bin": ["10111000"],
        "hex": ["0xB8"],
        "llvm": "mov_imm",
        "nasm": "MOV EAX, imm32",
    },
    0x56: {
        "bin": ["11000110"],
        "hex": ["0xC6"],
        "llvm": "mov_imm",
        "nasm": "MOV R/M8, imm8",
    },
    0x57: {
        "bin": ["11000111"],
        "hex": ["0xC7"],
        "llvm": "mov_imm",
        "nasm": "MOV R/M32, imm32",
    },
    0x58: {
        "bin": ["10001010"],
        "hex": ["0x8A"],
        "llvm": "mov",
        "nasm": "MOV R8, R/M8",
    },
    0x59: {
        "bin": ["10001011"],
        "hex": ["0x8B"],
        "llvm": "mov",
        "nasm": "MOV R32, R/M32",
    },
    0x5A: {
        "bin": ["10001000"],
        "hex": ["0x88"],
        "llvm": "mov",
        "nasm": "MOV R/M8, R8",
    },
    0x5B: {
        "bin": ["10001001"],
        "hex": ["0x89"],
        "llvm": "mov",
        "nasm": "MOV R/M32, R32",
    },
    0x5C: {
        "bin": ["10001100"],
        "hex": ["0x8C"],
        "llvm": "mov_seg",
        "nasm": "MOV R/M16, SREG",
    },
    0x5D: {
        "bin": ["10001110"],
        "hex": ["0x8E"],
        "llvm": "mov_seg",
        "nasm": "MOV SREG, R/M16",
    },
    0x5E: {
        "bin": ["10001111"],
        "hex": ["0x8F"],
        "llvm": "pop",
        "nasm": "POP R/M32",
    },
    0x5F: {
        "bin": ["01011001"],
        "hex": ["0x59"],
        "llvm": "pop",
        "nasm": "POP ECX",
    },
    0x60: {
        "bin": ["01010001"],
        "hex": ["0x51"],
        "llvm": "push",
        "nasm": "PUSH ECX",
    },
    0x61: {
        "bin": ["01010010"],
        "hex": ["0x52"],
        "llvm": "push",
        "nasm": "PUSH EDX",
    },
    0x62: {
        "bin": ["01010011"],
        "hex": ["0x53"],
        "llvm": "push",
        "nasm": "PUSH EBX",
    },
    0x63: {
        "bin": ["01011000"],
        "hex": ["0x58"],
        "llvm": "pop",
        "nasm": "POP EAX",
    },

      0x64: {
        "bin": ["01010101"],
        "hex": ["0x55"],
        "llvm": "push",
        "nasm": "PUSH EBP",
    },
    0x65: {
        "bin": ["01011101"],
        "hex": ["0x5D"],
        "llvm": "pop",
        "nasm": "POP EBP",
    },
    0x66: {
        "bin": ["01010110"],
        "hex": ["0x56"],
        "llvm": "push",
        "nasm": "PUSH ESI",
    },
    0x67: {
        "bin": ["01011110"],
        "hex": ["0x5E"],
        "llvm": "pop",
        "nasm": "POP ESI",
    },
    0x68: {
        "bin": ["01010111"],
        "hex": ["0x57"],
        "llvm": "push",
        "nasm": "PUSH EDI",
    },
    0x69: {
        "bin": ["01011111"],
        "hex": ["0x5F"],
        "llvm": "pop",
        "nasm": "POP EDI",
    },
    0x6A: {
        "bin": ["00001101"],
        "hex": ["0x0D"],
        "llvm": "int",
        "nasm": "INT imm8",
    },
    0x6B: {
        "bin": ["11001101"],
        "hex": ["0xCD"],
        "llvm": "int",
        "nasm": "INT imm8",
    },
    0x6C: {
        "bin": ["11001100"],
        "hex": ["0xCC"],
        "llvm": "int3",
        "nasm": "INT3",
    },
    0x6D: {
        "bin": ["11000011"],
        "hex": ["0xC3"],
        "llvm": "return",
        "nasm": "RET",
    },
    0x6E: {
        "bin": ["11000010"],
        "hex": ["0xC2"],
        "llvm": "return",
        "nasm": "RET imm16",
    },
    0x6F: {
        "bin": ["00000000"],
        "hex": ["0x00"],
        "llvm": "db",
        "nasm": "DB 0x00",
    },
    0x70: {
        "bin": ["11111111"],
        "hex": ["0xFF"],
        "llvm": "dd",
        "nasm": "DD imm32",
    },
    0x71: {
        "bin": ["10101010"],
        "hex": ["0xAA"],
        "llvm": "stosb",
        "nasm": "STOSB",
    },
    0x72: {
        "bin": ["10101011"],
        "hex": ["0xAB"],
        "llvm": "stosd",
        "nasm": "STOSD",
    },
    0x73: {
        "bin": ["10101000"],
        "hex": ["0xA8"],
        "llvm": "test",
        "nasm": "TEST AL, imm8",
    },

      0x74: {
        "bin": ["11110110"],
        "hex": ["0xF6"],
        "llvm": "test",
        "nasm": "TEST R/M8, imm8",
    },
    0x75: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "test",
        "nasm": "TEST R/M32, imm32",
    },
    0x76: {
        "bin": ["10000100"],
        "hex": ["0x84"],
        "llvm": "test",
        "nasm": "TEST R/M8, R8",
    },
    0x77: {
        "bin": ["10000101"],
        "hex": ["0x85"],
        "llvm": "test",
        "nasm": "TEST R/M32, R32",
    },
    0x78: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "inc",
        "nasm": "INC R/M32",
    },
    0x79: {
        "bin": ["01000111"],
        "hex": ["0x47"],
        "llvm": "inc",
        "nasm": "INC EDI",
    },
    0x7A: {
        "bin": ["11111111"],
        "hex": ["0xFF"],
        "llvm": "dec",
        "nasm": "DEC R/M32",
    },
    0x7B: {
        "bin": ["01001001"],
        "hex": ["0x49"],
        "llvm": "dec",
        "nasm": "DEC ECX",
    },
    0x7C: {
        "bin": ["11111111"],
        "hex": ["0xFF"],
        "llvm": "push",
        "nasm": "PUSH R/M32",
    },
    0x7D: {
        "bin": ["11111111"],
        "hex": ["0xFF"],
        "llvm": "pop",
        "nasm": "POP R/M32",
    },
    0x7E: {
        "bin": ["11101000"],
        "hex": ["0xE8"],
        "llvm": "call",
        "nasm": "CALL rel32",
    },
    0x7F: {
        "bin": ["11111111"],
        "hex": ["0xFF"],
        "llvm": "jmp",
        "nasm": "JMP R/M32",
    },
    0x80: {
        "bin": ["11101011"],
        "hex": ["0xEB"],
        "llvm": "jmp",
        "nasm": "JMP rel8",
    },
    0x81: {
        "bin": ["11101001"],
        "hex": ["0xE9"],
        "llvm": "jmp",
        "nasm": "JMP rel32",
    },
    0x82: {
        "bin": ["01110101"],
        "hex": ["0x75"],
        "llvm": "jne",
        "nasm": "JNE rel8",
    },
    0x83: {
        "bin": ["01110100"],
        "hex": ["0x74"],
        "llvm": "je",
        "nasm": "JE rel8",
    },

      0x84: {
        "bin": ["01111100"],
        "hex": ["0x7C"],
        "llvm": "jl",
        "nasm": "JL rel8",
    },
    0x85: {
        "bin": ["01111110"],
        "hex": ["0x7E"],
        "llvm": "jle",
        "nasm": "JLE rel8",
    },
    0x86: {
        "bin": ["01111111"],
        "hex": ["0x7F"],
        "llvm": "jg",
        "nasm": "JG rel8",
    },
    0x87: {
        "bin": ["01111101"],
        "hex": ["0x7D"],
        "llvm": "jge",
        "nasm": "JGE rel8",
    },
    0x88: {
        "bin": ["01111010"],
        "hex": ["0x7A"],
        "llvm": "jp",
        "nasm": "JP rel8",
    },
    0x89: {
        "bin": ["01111011"],
        "hex": ["0x7B"],
        "llvm": "jnp",
        "nasm": "JNP rel8",
    },
    0x8A: {
        "bin": ["01110000"],
        "hex": ["0x70"],
        "llvm": "jo",
        "nasm": "JO rel8",
    },
    0x8B: {
        "bin": ["01110001"],
        "hex": ["0x71"],
        "llvm": "jno",
        "nasm": "JNO rel8",
    },
    0x8C: {
        "bin": ["01111000"],
        "hex": ["0x78"],
        "llvm": "js",
        "nasm": "JS rel8",
    },
    0x8D: {
        "bin": ["01111001"],
        "hex": ["0x79"],
        "llvm": "jns",
        "nasm": "JNS rel8",
    },
    0x8E: {
        "bin": ["01110110"],
        "hex": ["0x76"],
        "llvm": "jbe",
        "nasm": "JBE rel8",
    },
    0x8F: {
        "bin": ["01110111"],
        "hex": ["0x77"],
        "llvm": "ja",
        "nasm": "JA rel8",
    },
    0x90: {
        "bin": ["01110100"],
        "hex": ["0x74"],
        "llvm": "jz",
        "nasm": "JZ rel8",
    },
    0x91: {
        "bin": ["01110101"],
        "hex": ["0x75"],
        "llvm": "jnz",
        "nasm": "JNZ rel8",
    },
    0x92: {
        "bin": ["01110010"],
        "hex": ["0x72"],
        "llvm": "jb",
        "nasm": "JB rel8",
    },
    0x93: {
        "bin": ["01110011"],
        "hex": ["0x73"],
        "llvm": "jae",
        "nasm": "JAE rel8",
    },

      0x94: {
        "bin": ["10011100"],
        "hex": ["0x9C"],
        "llvm": "pushf",
        "nasm": "PUSHF",
    },
    0x95: {
        "bin": ["10011101"],
        "hex": ["0x9D"],
        "llvm": "popf",
        "nasm": "POPF",
    },
    0x96: {
        "bin": ["10011110"],
        "hex": ["0x9E"],
        "llvm": "sahf",
        "nasm": "SAHF",
    },
    0x97: {
        "bin": ["10011111"],
        "hex": ["0x9F"],
        "llvm": "lahf",
        "nasm": "LAHF",
    },
    0x98: {
        "bin": ["10011000"],
        "hex": ["0x98"],
        "llvm": "cbw",
        "nasm": "CBW",
    },
    0x99: {
        "bin": ["10011001"],
        "hex": ["0x99"],
        "llvm": "cwd",
        "nasm": "CWD",
    },
    0x9A: {
        "bin": ["10011010"],
        "hex": ["0x9A"],
        "llvm": "callf",
        "nasm": "CALLF ptr16:32",
    },
    0x9B: {
        "bin": ["10011011"],
        "hex": ["0x9B"],
        "llvm": "wait",
        "nasm": "WAIT",
    },
    0x9C: {
        "bin": ["10100100"],
        "hex": ["0xA4"],
        "llvm": "movsb",
        "nasm": "MOVSB",
    },
    0x9D: {
        "bin": ["10100101"],
        "hex": ["0xA5"],
        "llvm": "movsd",
        "nasm": "MOVSD",
    },
    0x9E: {
        "bin": ["10100110"],
        "hex": ["0xA6"],
        "llvm": "cmpsb",
        "nasm": "CMPSB",
    },
    0x9F: {
        "bin": ["10100111"],
        "hex": ["0xA7"],
        "llvm": "cmpsd",
        "nasm": "CMPSD",
    },
    0xA0: {
        "bin": ["10101100"],
        "hex": ["0xAC"],
        "llvm": "lodsb",
        "nasm": "LODSB",
    },
    0xA1: {
        "bin": ["10101101"],
        "hex": ["0xAD"],
        "llvm": "lodsd",
        "nasm": "LODSD",
    },
    0xA2: {
        "bin": ["10101110"],
        "hex": ["0xAE"],
        "llvm": "scasb",
        "nasm": "SCASB",
    },
    0xA3: {
        "bin": ["10101111"],
        "hex": ["0xAF"],
        "llvm": "scasd",
        "nasm": "SCASD",
    },

    0xA4: {
        "bin": ["10010100"],
        "hex": ["0x94"],
        "llvm": "xchg",
        "nasm": "XCHG EAX, ESP",
    },
    0xA5: {
        "bin": ["10010101"],
        "hex": ["0x95"],
        "llvm": "xchg",
        "nasm": "XCHG EAX, EBP",
    },
    0xA6: {
        "bin": ["10010110"],
        "hex": ["0x96"],
        "llvm": "xchg",
        "nasm": "XCHG EAX, ESI",
    },
    0xA7: {
        "bin": ["10010111"],
        "hex": ["0x97"],
        "llvm": "xchg",
        "nasm": "XCHG EAX, EDI",
    },
    0xA8: {
        "bin": ["10010000"],
        "hex": ["0x90"],
        "llvm": "nop",
        "nasm": "NOP",
    },
    0xA9: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "cmp",
        "nasm": "CMP R/M32, imm32",
    },
    0xAA: {
        "bin": ["00111001"],
        "hex": ["0x39"],
        "llvm": "cmp",
        "nasm": "CMP R/M32, R32",
    },
    0xAB: {
        "bin": ["00111011"],
        "hex": ["0x3B"],
        "llvm": "cmp",
        "nasm": "CMP R32, R/M32",
    },
    0xAC: {
        "bin": ["10000011"],
        "hex": ["0x83"],
        "llvm": "cmp",
        "nasm": "CMP R/M32, imm8",
    },
    0xAD: {
        "bin": ["10000001"],
        "hex": ["0x81"],
        "llvm": "cmp",
        "nasm": "CMP R/M32, imm32",
    },
    0xAE: {
        "bin": ["11110110"],
        "hex": ["0xF6"],
        "llvm": "mul",
        "nasm": "MUL R/M8",
    },
    0xAF: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "mul",
        "nasm": "MUL R/M32",
    },
    0xB0: {
        "bin": ["11110110"],
        "hex": ["0xF6"],
        "llvm": "imul",
        "nasm": "IMUL R/M8",
    },
    0xB1: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "imul",
        "nasm": "IMUL R/M32",
    },
    0xB2: {
        "bin": ["11110110"],
        "hex": ["0xF6"],
        "llvm": "div",
        "nasm": "DIV R/M8",
    },
    0xB3: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "div",
        "nasm": "DIV R/M32",
    },

      0xB4: {
        "bin": ["11110110"],
        "hex": ["0xF6"],
        "llvm": "idiv",
        "nasm": "IDIV R/M8",
    },
    0xB5: {
        "bin": ["11110111"],
        "hex": ["0xF7"],
        "llvm": "idiv",
        "nasm": "IDIV R/M32",
    },
    0xB6: {
        "bin": ["10011110"],
        "hex": ["0x9E"],
        "llvm": "setp",
        "nasm": "SETP R/M8",
    },
    0xB7: {
        "bin": ["10011111"],
        "hex": ["0x9F"],
        "llvm": "setnp",
        "nasm": "SETNP R/M8",
    },
    0xB8: {
        "bin": ["10011100"],
        "hex": ["0x9C"],
        "llvm": "setl",
        "nasm": "SETL R/M8",
    },
    0xB9: {
        "bin": ["10011101"],
        "hex": ["0x9D"],
        "llvm": "setnl",
        "nasm": "SETNL R/M8",
    },
    0xBA: {
        "bin": ["10011010"],
        "hex": ["0x9A"],
        "llvm": "seto",
        "nasm": "SETO R/M8",
    },
    0xBB: {
        "bin": ["10011011"],
        "hex": ["0x9B"],
        "llvm": "setno",
        "nasm": "SETNO R/M8",
    },
}

DGM_TABLE_LEN = 144

# ------------------------------
# Color helper
# ------------------------------
USE_COLOR = True

def color(text, c):
    if not USE_COLOR:
        return text
    return c + text + Style.RESET_ALL

# ------------------------------
# Features
# ------------------------------
def print_version():
    print(version_string())

def search_opcodes(keyword):
    keyword = keyword.lower()
    results = {}
    for op, data in DGM_TABLE.items():
        if (keyword in hex(op).lower() or
            any(keyword in h.lower() for h in data["hex"]) or
            any(keyword in b.lower() for b in data["bin"]) or
            keyword in data["llvm"].lower() or
            keyword in data["nasm"].lower()):
            results[hex(op)] = data
    print(json.dumps(results, indent=4))

def dump_table(grouped=False):
    if not grouped:
        print(json.dumps(DGM_TABLE, indent=4))
    else:
        grouped_dict = {
            "Memory": {k: v for k, v in DGM_TABLE.items() if k <= 0x0A},
            "Arithmetic": {k: v for k, v in DGM_TABLE.items() if 0x0B <= k <= 0x1A},
            "Logic": {k: v for k, v in DGM_TABLE.items() if 0x1B <= k <= 0x2D},
            "ControlFlow": {k: v for k, v in DGM_TABLE.items() if 0x2E <= k <= 0x3F},
            "Terminators": {k: v for k, v in DGM_TABLE.items() if 0x40 <= k <= 0x53},
            "LanguageOps": {k: v for k, v in DGM_TABLE.items() if k >= 0x54},
        }
        print(json.dumps(grouped_dict, indent=4))

def print_stats():
    groups = {
        "Memory": range(0x00, 0x0B),
        "Arithmetic": range(0x0B, 0x1B),
        "Logic": range(0x1B, 0x2E),
        "ControlFlow": range(0x2E, 0x40),
        "Terminators": range(0x40, 0x54),
        "LanguageOps": range(0x54, 0xBC),
    }
    for name, rng in groups.items():
        count = sum(1 for op in rng if op in DGM_TABLE)
        print(color(f"{name}: {count}", Fore.CYAN))

def event_reader():
    for line in sys.stdin:
        key = line.strip()
        try:
            opcode = int(key, 16)
            if opcode in DGM_TABLE:
                print(json.dumps({hex(opcode): DGM_TABLE[opcode]}, indent=4))
            else:
                print(color(f"Unknown opcode: {key}", Fore.RED))
        except ValueError:
            print(color(f"Invalid input: {key}", Fore.RED))

# ------------------------------
# Main CLI
# ------------------------------
def main():
    global USE_COLOR
    parser = argparse.ArgumentParser(description="DGM → LLVM IR → NASM Translator", add_help=False)
    parser.add_argument("opcode", nargs="?", help="Opcode to look up (e.g., 0x17)")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--search", metavar="KEY", help="Search opcode table by keyword")
    parser.add_argument("--dump-table", action="store_true", help="Dump full opcode table as JSON")
    parser.add_argument("--grouped-dump", action="store_true", help="Dump grouped opcode table as JSON")
    parser.add_argument("--stats", action="store_true", help="Show opcode counts per group")
    parser.add_argument("--event-reader", action="store_true", help="Read opcodes from stdin")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--help", action="store_true", help="Show this help message")

    args = parser.parse_args()
    USE_COLOR = not args.no_color

    if args.help:
        parser.print_help()
        return
    if args.version:
        print_version()
        return
    if args.search:
        search_opcodes(args.search)
        return
    if args.dump_table:
        dump_table()
        return
    if args.grouped_dump:
        dump_table(grouped=True)
        return
    if args.stats:
        print_stats()
        return
    if args.event_reader:
        event_reader()
        return
    if args.opcode:
        try:
            opcode = int(args.opcode, 16)
            if opcode in DGM_TABLE:
                print(json.dumps({hex(opcode): DGM_TABLE[opcode]}, indent=4))
            else:
                print(color(f"Unknown opcode: {args.opcode}", Fore.RED))
        except ValueError:
            print(color(f"Invalid opcode: {args.opcode}", Fore.RED))
        return

    parser.print_help()

if __name__ == "__main__":
    main()

# ------------------------------
# CHANGELOG
# ------------------------------
# v1.0.0 - Initial release
# - Added 144 opcode entries (0x00 → 0xBB)
# - CLI with search, dump, grouped-dump, stats, event-reader
# - Pretty JSON and colorized output
# - --no-color flag for CI/plaintext use
