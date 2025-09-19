#!/usr/bin/env python3
"""
executor.py — Full VM executor for DGM opcodes (0x00 → 0xBB)
Version: 1.0.0

Depends on codegen.py for DGM_TABLE definitions.
"""

import sys
import json
import argparse
from codegen import DGM_TABLE, DGM_TABLE_LEN, version_string, color, Fore

# ------------------------------
# VM Definition
# ------------------------------
class VM:
    def __init__(self, mem_size=65536):
        # General-purpose registers (32-bit)
        self.registers = {
            "EAX": 0,
            "EBX": 0,
            "ECX": 0,
            "EDX": 0,
            "ESI": 0,
            "EDI": 0,
            "EBP": 0,
            "ESP": mem_size - 4,  # stack grows down
            "EIP": 0,
        }

        # Flags (x86 style)
        self.flags = {
            "ZF": 0,  # Zero
            "CF": 0,  # Carry
            "SF": 0,  # Sign
            "OF": 0,  # Overflow
            "PF": 0,  # Parity
            "AF": 0,  # Adjust
        }

        # Memory as bytearray
        self.memory = bytearray(mem_size)

        # Execution state
        self.halted = False

    # --------------------------
    # Helpers
    # --------------------------
    def push(self, value):
        """Push a 32-bit value on the stack"""
        self.registers["ESP"] -= 4
        addr = self.registers["ESP"]
        self.memory[addr:addr+4] = value.to_bytes(4, byteorder="little", signed=False)

    def pop(self):
        """Pop a 32-bit value from the stack"""
        addr = self.registers["ESP"]
        value = int.from_bytes(self.memory[addr:addr+4], byteorder="little", signed=False)
        self.registers["ESP"] += 4
        return value

    def read_mem(self, addr, size=4):
        return int.from_bytes(self.memory[addr:addr+size], byteorder="little", signed=False)

    def write_mem(self, addr, value, size=4):
        self.memory[addr:addr+size] = value.to_bytes(size, byteorder="little", signed=False)

    def update_flags_arithmetic(self, result, bits=32):
        """Set ZF, SF, OF, PF flags for arithmetic result"""
        mask = (1 << bits) - 1
        signed_mask = 1 << (bits - 1)
        res = result & mask

        self.flags["ZF"] = int(res == 0)
        self.flags["SF"] = int((res & signed_mask) != 0)
        # Overflow/carry approximations
        self.flags["CF"] = int(result != res)
        self.flags["OF"] = 0  # Simplified (would need operand signs)
        self.flags["PF"] = int(bin(res & 0xFF).count("1") % 2 == 0)
        self.flags["AF"] = 0  # Not tracked in this version

    def dump_state(self):
        return {
            "registers": self.registers,
            "flags": self.flags,
        }

# ------------------------------
# Executor
# ------------------------------
class Executor:
    def __init__(self, trace=False):
        self.vm = VM()
        self.trace = trace

    def log(self, msg, color_fn=Fore.CYAN):
        if self.trace:
            print(color(f"[TRACE] {msg}", color_fn))

    def execute(self, opcode):
        if opcode not in OPCODE_EXECUTORS:
            return f"Unknown opcode: {hex(opcode)}"

        handler = OPCODE_EXECUTORS[opcode]
        result = handler(self.vm, opcode)

        if self.trace:
            self.log(f"{hex(opcode)} → {DGM_TABLE[opcode]['llvm']} ({DGM_TABLE[opcode]['nasm']})", Fore.GREEN)

        return result

# ------------------------------
# Opcode Handlers
# ------------------------------
def op_nop(vm, opcode):
    vm.log = None
    return "NOP"

def op_hlt(vm, opcode):
    vm.halted = True
    return "HALT"

# Example arithmetic handlers
def op_add(vm, opcode):
    eax = vm.registers["EAX"]
    ebx = vm.registers["EBX"]
    result = eax + ebx
    vm.registers["EAX"] = result & 0xFFFFFFFF
    vm.update_flags_arithmetic(result)
    return f"ADD EAX, EBX = {vm.registers['EAX']}"

def op_sub(vm, opcode):
    eax = vm.registers["EAX"]
    ebx = vm.registers["EBX"]
    result = eax - ebx
    vm.registers["EAX"] = result & 0xFFFFFFFF
    vm.update_flags_arithmetic(result)
    return f"SUB EAX, EBX = {vm.registers['EAX']}"

def op_inc(vm, opcode):
    vm.registers["EAX"] = (vm.registers["EAX"] + 1) & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"INC EAX = {vm.registers['EAX']}"

def op_dec(vm, opcode):
    vm.registers["EAX"] = (vm.registers["EAX"] - 1) & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"DEC EAX = {vm.registers['EAX']}"

# Example stack handlers
def op_push_eax(vm, opcode):
    vm.push(vm.registers["EAX"])
    return f"PUSH EAX ({vm.registers['EAX']})"

def op_pop_eax(vm, opcode):
    vm.registers["EAX"] = vm.pop()
    return f"POP → EAX = {vm.registers['EAX']}"

# ------------------------------
# Dispatcher Table
# ------------------------------
OPCODE_EXECUTORS = {
    0x00: op_nop,
    0x40: op_hlt,
    0x0B: op_add,
    0x0F: op_sub,
    0x78: op_inc,
    0x7A: op_dec,
    0x60: op_push_eax,
    0x63: op_pop_eax,
    # ... we will continue filling in all 144 opcodes
}

# ------------------------------
# Arithmetic Handlers
# ------------------------------
def op_add_eax_ebx(vm, opcode):
    eax = vm.registers["EAX"]
    ebx = vm.registers["EBX"]
    result = eax + ebx
    vm.registers["EAX"] = result & 0xFFFFFFFF
    vm.update_flags_arithmetic(result)
    return f"ADD EAX, EBX → {vm.registers['EAX']}"

def op_sub_eax_ebx(vm, opcode):
    eax = vm.registers["EAX"]
    ebx = vm.registers["EBX"]
    result = eax - ebx
    vm.registers["EAX"] = result & 0xFFFFFFFF
    vm.update_flags_arithmetic(result)
    return f"SUB EAX, EBX → {vm.registers['EAX']}"

def op_mul_eax_ebx(vm, opcode):
    eax = vm.registers["EAX"]
    ebx = vm.registers["EBX"]
    result = eax * ebx
    vm.registers["EAX"] = result & 0xFFFFFFFF
    vm.update_flags_arithmetic(result)
    return f"MUL EAX, EBX → {vm.registers['EAX']}"

def op_imul_eax_ebx(vm, opcode):
    eax = vm.registers["EAX"]
    ebx = vm.registers["EBX"]
    result = (eax * ebx) & 0xFFFFFFFF
    vm.registers["EAX"] = result
    vm.update_flags_arithmetic(result)
    return f"IMUL EAX, EBX → {vm.registers['EAX']}"

def op_div_eax_ebx(vm, opcode):
    ebx = vm.registers["EBX"]
    if ebx == 0:
        vm.halted = True
        return "DIV by zero → HALT"
    eax = vm.registers["EAX"]
    vm.registers["EAX"] = eax // ebx
    vm.registers["EDX"] = eax % ebx
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"DIV EAX/EBX → EAX={vm.registers['EAX']} EDX={vm.registers['EDX']}"

def op_idiv_eax_ebx(vm, opcode):
    ebx = vm.registers["EBX"]
    if ebx == 0:
        vm.halted = True
        return "IDIV by zero → HALT"
    eax = vm.registers["EAX"]
    vm.registers["EAX"] = int(eax / ebx)
    vm.registers["EDX"] = eax % ebx
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"IDIV EAX/EBX → EAX={vm.registers['EAX']} EDX={vm.registers['EDX']}"

def op_inc_eax(vm, opcode):
    vm.registers["EAX"] = (vm.registers["EAX"] + 1) & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"INC EAX → {vm.registers['EAX']}"

def op_dec_eax(vm, opcode):
    vm.registers["EAX"] = (vm.registers["EAX"] - 1) & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"DEC EAX → {vm.registers['EAX']}"

# ------------------------------
# Logic Handlers
# ------------------------------
def op_and_eax_ebx(vm, opcode):
    vm.registers["EAX"] &= vm.registers["EBX"]
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"AND EAX, EBX → {vm.registers['EAX']}"

def op_or_eax_ebx(vm, opcode):
    vm.registers["EAX"] |= vm.registers["EBX"]
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"OR EAX, EBX → {vm.registers['EAX']}"

def op_xor_eax_ebx(vm, opcode):
    vm.registers["EAX"] ^= vm.registers["EBX"]
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"XOR EAX, EBX → {vm.registers['EAX']}"

def op_not_eax(vm, opcode):
    vm.registers["EAX"] = (~vm.registers["EAX"]) & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"NOT EAX → {vm.registers['EAX']}"

def op_shl_eax(vm, opcode):
    vm.registers["EAX"] = (vm.registers["EAX"] << 1) & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"SHL EAX, 1 → {vm.registers['EAX']}"

def op_shr_eax(vm, opcode):
    vm.registers["EAX"] = (vm.registers["EAX"] >> 1) & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"SHR EAX, 1 → {vm.registers['EAX']}"

def op_sar_eax(vm, opcode):
    eax = vm.registers["EAX"]
    vm.registers["EAX"] = (eax >> 1) | (eax & 0x80000000)
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"SAR EAX, 1 → {vm.registers['EAX']}"

# ------------------------------
# Control Flow Handlers
# ------------------------------
def op_jmp_rel8(vm, opcode):
    vm.registers["EIP"] += 1  # simulate short jump
    return f"JMP rel8 → EIP={vm.registers['EIP']}"

def op_jmp_rel32(vm, opcode):
    vm.registers["EIP"] += 4
    return f"JMP rel32 → EIP={vm.registers['EIP']}"

def op_call_rel32(vm, opcode):
    vm.push(vm.registers["EIP"] + 4)
    vm.registers["EIP"] += 4
    return f"CALL rel32 → pushed return, EIP={vm.registers['EIP']}"

def op_call_rm32(vm, opcode):
    vm.push(vm.registers["EIP"])
    vm.registers["EIP"] = vm.registers["EAX"]  # assume EAX holds target
    return f"CALL R/M32 → EIP={vm.registers['EIP']}"

def op_ret(vm, opcode):
    vm.registers["EIP"] = vm.pop()
    return f"RET → EIP={vm.registers['EIP']}"

def op_ret_imm16(vm, opcode):
    vm.registers["EIP"] = vm.pop()
    vm.registers["ESP"] += 2
    return f"RET imm16 → EIP={vm.registers['EIP']}"

def op_int(vm, opcode):
    vm.push(vm.registers["EIP"])
    vm.registers["EIP"] = 0x80  # trap vector
    return "INT imm8 → simulated interrupt"

def op_int3(vm, opcode):
    vm.push(vm.registers["EIP"])
    vm.registers["EIP"] = 0xCC
    return "INT3 → simulated breakpoint"

def op_jcc(vm, opcode, cond):
    if cond(vm):
        vm.registers["EIP"] += 1
        return f"Branch taken → EIP={vm.registers['EIP']}"
    else:
        return "Branch not taken"

# Condition helpers
def cond_zf(vm): return vm.flags["ZF"] == 1
def cond_nz(vm): return vm.flags["ZF"] == 0
def cond_sf(vm): return vm.flags["SF"] == 1
def cond_ns(vm): return vm.flags["SF"] == 0
def cond_of(vm): return vm.flags["OF"] == 1
def cond_no(vm): return vm.flags["OF"] == 0
def cond_cf(vm): return vm.flags["CF"] == 1
def cond_nc(vm): return vm.flags["CF"] == 0

# ------------------------------
# Terminator Handlers
# ------------------------------
def op_hlt(vm, opcode):
    vm.halted = True
    return "HLT → execution halted"

def op_cmc(vm, opcode):
    vm.flags["CF"] ^= 1
    return f"CMC → CF={vm.flags['CF']}"

def op_clc(vm, opcode):
    vm.flags["CF"] = 0
    return "CLC → CF=0"

def op_stc(vm, opcode):
    vm.flags["CF"] = 1
    return "STC → CF=1"

def op_cli(vm, opcode):
    return "CLI → interrupts disabled (simulated)"

def op_sti(vm, opcode):
    return "STI → interrupts enabled (simulated)"

def op_cld(vm, opcode):
    return "CLD → direction flag cleared (simulated)"

def op_std(vm, opcode):
    return "STD → direction flag set (simulated)"

def op_iret(vm, opcode):
    vm.registers["EIP"] = vm.pop()
    return f"IRET → EIP={vm.registers['EIP']}"

def op_loop(vm, opcode):
    vm.registers["ECX"] -= 1
    if vm.registers["ECX"] != 0:
        vm.registers["EIP"] += 1
        return f"LOOP → ECX={vm.registers['ECX']} (taken)"
    return f"LOOP → ECX={vm.registers['ECX']} (not taken)"

def op_loope(vm, opcode):
    vm.registers["ECX"] -= 1
    if vm.registers["ECX"] != 0 and vm.flags["ZF"] == 1:
        vm.registers["EIP"] += 1
        return f"LOOPE → ECX={vm.registers['ECX']} ZF=1 (taken)"
    return "LOOPE → not taken"

def op_loopne(vm, opcode):
    vm.registers["ECX"] -= 1
    if vm.registers["ECX"] != 0 and vm.flags["ZF"] == 0:
        vm.registers["EIP"] += 1
        return f"LOOPNE → ECX={vm.registers['ECX']} ZF=0 (taken)"
    return "LOOPNE → not taken"

# ------------------------------
# Language Ops Handlers
# ------------------------------
def op_mov_imm_eax(vm, opcode):
    vm.registers["EAX"] = 1  # simulated imm32
    return f"MOV EAX, imm32 → {vm.registers['EAX']}"

def op_mov_r32_rm32(vm, opcode):
    vm.registers["EAX"] = vm.registers["EBX"]
    return f"MOV EAX, EBX → {vm.registers['EAX']}"

def op_mov_rm32_r32(vm, opcode):
    vm.registers["EBX"] = vm.registers["EAX"]
    return f"MOV EBX, EAX → {vm.registers['EBX']}"

def op_push_ecx(vm, opcode):
    vm.push(vm.registers["ECX"])
    return f"PUSH ECX → {vm.registers['ECX']}"

def op_pop_ecx(vm, opcode):
    vm.registers["ECX"] = vm.pop()
    return f"POP ECX → {vm.registers['ECX']}"

def op_push_edx(vm, opcode):
    vm.push(vm.registers["EDX"])
    return f"PUSH EDX → {vm.registers['EDX']}"

def op_pop_edx(vm, opcode):
    vm.registers["EDX"] = vm.pop()
    return f"POP EDX → {vm.registers['EDX']}"

def op_push_ebx(vm, opcode):
    vm.push(vm.registers["EBX"])
    return f"PUSH EBX → {vm.registers['EBX']}"

def op_pop_ebx(vm, opcode):
    vm.registers["EBX"] = vm.pop()
    return f"POP EBX → {vm.registers['EBX']}"

def op_push_eax(vm, opcode):
    vm.push(vm.registers["EAX"])
    return f"PUSH EAX → {vm.registers['EAX']}"

def op_pop_eax(vm, opcode):
    vm.registers["EAX"] = vm.pop()
    return f"POP EAX → {vm.registers['EAX']}"

def op_push_ebp(vm, opcode):
    vm.push(vm.registers["EBP"])
    return f"PUSH EBP → {vm.registers['EBP']}"

def op_pop_ebp(vm, opcode):
    vm.registers["EBP"] = vm.pop()
    return f"POP EBP → {vm.registers['EBP']}"

def op_push_esi(vm, opcode):
    vm.push(vm.registers["ESI"])
    return f"PUSH ESI → {vm.registers['ESI']}"

def op_pop_esi(vm, opcode):
    vm.registers["ESI"] = vm.pop()
    return f"POP ESI → {vm.registers['ESI']}"

def op_push_edi(vm, opcode):
    vm.push(vm.registers["EDI"])
    return f"PUSH EDI → {vm.registers['EDI']}"

def op_pop_edi(vm, opcode):
    vm.registers["EDI"] = vm.pop()
    return f"POP EDI → {vm.registers['EDI']}"

def op_push_ebp(vm, opcode):
    vm.push(vm.registers["EBP"])
    return f"PUSH EBP → {vm.registers['EBP']}"

def op_pop_ebp(vm, opcode):
    vm.registers["EBP"] = vm.pop()
    return f"POP EBP → {vm.registers['EBP']}"

def op_int(vm, opcode):
    vm.push(vm.registers["EIP"])
    vm.registers["EIP"] = 0x80
    return "INT imm8 → simulated software interrupt"

def op_int3(vm, opcode):
    vm.push(vm.registers["EIP"])
    vm.registers["EIP"] = 0xCC
    return "INT3 → simulated breakpoint"

def op_ret(vm, opcode):
    vm.registers["EIP"] = vm.pop()
    return f"RET → EIP={vm.registers['EIP']}"

def op_ret_imm16(vm, opcode):
    vm.registers["EIP"] = vm.pop()
    vm.registers["ESP"] += 2
    return f"RET imm16 → EIP={vm.registers['EIP']}"

def op_stosb(vm, opcode):
    addr = vm.registers["EDI"]
    vm.memory[addr] = vm.registers["EAX"] & 0xFF
    vm.registers["EDI"] += 1
    return f"STOSB → MEM[{addr}]={vm.memory[addr]}"

def op_stosd(vm, opcode):
    addr = vm.registers["EDI"]
    val = vm.registers["EAX"]
    vm.write_mem(addr, val, 4)
    vm.registers["EDI"] += 4
    return f"STOSD → MEM[{addr}]={val}"

def op_test_al_imm8(vm, opcode):
    imm = 1  # placeholder immediate
    res = (vm.registers["EAX"] & 0xFF) & imm
    vm.update_flags_arithmetic(res, bits=8)
    return f"TEST AL, {imm} → ZF={vm.flags['ZF']}"

def op_test_eax_imm32(vm, opcode):
    imm = 1  # placeholder immediate
    res = vm.registers["EAX"] & imm
    vm.update_flags_arithmetic(res)
    return f"TEST EAX, {imm} → ZF={vm.flags['ZF']}"

def op_test_rm8_r8(vm, opcode):
    res = (vm.registers["EAX"] & 0xFF) & (vm.registers["EBX"] & 0xFF)
    vm.update_flags_arithmetic(res, bits=8)
    return f"TEST R/M8, R8 → ZF={vm.flags['ZF']}"

def op_test_rm32_r32(vm, opcode):
    res = vm.registers["EAX"] & vm.registers["EBX"]
    vm.update_flags_arithmetic(res)
    return f"TEST R/M32, R32 → ZF={vm.flags['ZF']}"

def op_inc_edi(vm, opcode):
    vm.registers["EDI"] = (vm.registers["EDI"] + 1) & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EDI"])
    return f"INC EDI → {vm.registers['EDI']}"

def op_dec_ecx(vm, opcode):
    vm.registers["ECX"] = (vm.registers["ECX"] - 1) & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["ECX"])
    return f"DEC ECX → {vm.registers['ECX']}"

def op_push_rm32(vm, opcode):
    vm.push(vm.registers["EAX"])
    return f"PUSH R/M32 → {vm.registers['EAX']}"

def op_pop_rm32(vm, opcode):
    vm.registers["EAX"] = vm.pop()
    return f"POP R/M32 → {vm.registers['EAX']}"

def op_call_rel32(vm, opcode):
    vm.push(vm.registers["EIP"])
    vm.registers["EIP"] += 4
    return f"CALL rel32 → pushed return, EIP={vm.registers['EIP']}"

def op_jmp_rm32(vm, opcode):
    vm.registers["EIP"] = vm.registers["EAX"]
    return f"JMP R/M32 → EIP={vm.registers['EIP']}"

def op_jmp_rel8(vm, opcode):
    vm.registers["EIP"] += 1
    return f"JMP rel8 → EIP={vm.registers['EIP']}"

def op_jmp_rel32(vm, opcode):
    vm.registers["EIP"] += 4
    return f"JMP rel32 → EIP={vm.registers['EIP']}"

def op_jne_rel8(vm, opcode):
    if vm.flags["ZF"] == 0:
        vm.registers["EIP"] += 1
        return f"JNE rel8 → taken, EIP={vm.registers['EIP']}"
    return "JNE rel8 → not taken"

def op_je_rel8(vm, opcode):
    if vm.flags["ZF"] == 1:
        vm.registers["EIP"] += 1
        return f"JE rel8 → taken, EIP={vm.registers['EIP']}"
    return "JE rel8 → not taken"

def op_jl_rel8(vm, opcode):
    if vm.flags["SF"] != vm.flags["OF"]:
        vm.registers["EIP"] += 1
        return f"JL rel8 → taken, EIP={vm.registers['EIP']}"
    return "JL rel8 → not taken"

def op_jle_rel8(vm, opcode):
    if vm.flags["ZF"] == 1 or vm.flags["SF"] != vm.flags["OF"]:
        vm.registers["EIP"] += 1
        return f"JLE rel8 → taken, EIP={vm.registers['EIP']}"
    return "JLE rel8 → not taken"

def op_jg_rel8(vm, opcode):
    if vm.flags["ZF"] == 0 and vm.flags["SF"] == vm.flags["OF"]:
        vm.registers["EIP"] += 1
        return f"JG rel8 → taken, EIP={vm.registers['EIP']}"
    return "JG rel8 → not taken"

def op_jge_rel8(vm, opcode):
    if vm.flags["SF"] == vm.flags["OF"]:
        vm.registers["EIP"] += 1
        return f"JGE rel8 → taken, EIP={vm.registers['EIP']}"
    return "JGE rel8 → not taken"

def op_jp_rel8(vm, opcode):
    if vm.flags["PF"] == 1:
        vm.registers["EIP"] += 1
        return f"JP rel8 → taken, EIP={vm.registers['EIP']}"
    return "JP rel8 → not taken"

def op_jnp_rel8(vm, opcode):
    if vm.flags["PF"] == 0:
        vm.registers["EIP"] += 1
        return f"JNP rel8 → taken, EIP={vm.registers['EIP']}"
    return "JNP rel8 → not taken"

def op_jo_rel8(vm, opcode):
    if vm.flags["OF"] == 1:
        vm.registers["EIP"] += 1
        return f"JO rel8 → taken, EIP={vm.registers['EIP']}"
    return "JO rel8 → not taken"

def op_jno_rel8(vm, opcode):
    if vm.flags["OF"] == 0:
        vm.registers["EIP"] += 1
        return f"JNO rel8 → taken, EIP={vm.registers['EIP']}"
    return "JNO rel8 → not taken"

def op_js_rel8(vm, opcode):
    if vm.flags["SF"] == 1:
        vm.registers["EIP"] += 1
        return f"JS rel8 → taken, EIP={vm.registers['EIP']}"
    return "JS rel8 → not taken"

def op_jns_rel8(vm, opcode):
    if vm.flags["SF"] == 0:
        vm.registers["EIP"] += 1
        return f"JNS rel8 → taken, EIP={vm.registers['EIP']}"
    return "JNS rel8 → not taken"

def op_jbe_rel8(vm, opcode):
    if vm.flags["CF"] == 1 or vm.flags["ZF"] == 1:
        vm.registers["EIP"] += 1
        return f"JBE rel8 → taken, EIP={vm.registers['EIP']}"
    return "JBE rel8 → not taken"

def op_ja_rel8(vm, opcode):
    if vm.flags["CF"] == 0 and vm.flags["ZF"] == 0:
        vm.registers["EIP"] += 1
        return f"JA rel8 → taken, EIP={vm.registers['EIP']}"
    return "JA rel8 → not taken"

def op_jz_rel8(vm, opcode):
    if vm.flags["ZF"] == 1:
        vm.registers["EIP"] += 1
        return f"JZ rel8 → taken, EIP={vm.registers['EIP']}"
    return "JZ rel8 → not taken"

def op_jnz_rel8(vm, opcode):
    if vm.flags["ZF"] == 0:
        vm.registers["EIP"] += 1
        return f"JNZ rel8 → taken, EIP={vm.registers['EIP']}"
    return "JNZ rel8 → not taken"

def op_jb_rel8(vm, opcode):
    if vm.flags["CF"] == 1:
        vm.registers["EIP"] += 1
        return f"JB rel8 → taken, EIP={vm.registers['EIP']}"
    return "JB rel8 → not taken"

def op_jae_rel8(vm, opcode):
    if vm.flags["CF"] == 0:
        vm.registers["EIP"] += 1
        return f"JAE rel8 → taken, EIP={vm.registers['EIP']}"
    return "JAE rel8 → not taken"

def op_pushf(vm, opcode):
    flags_val = sum((v << i) for i, v in enumerate(vm.flags.values()))
    vm.push(flags_val)
    return f"PUSHF → {flags_val:#010x}"

def op_popf(vm, opcode):
    val = vm.pop()
    i = 0
    for key in vm.flags.keys():
        vm.flags[key] = (val >> i) & 1
        i += 1
    return f"POPF → flags restored {vm.flags}"

def op_sahf(vm, opcode):
    ah = (vm.registers["EAX"] >> 8) & 0xFF
    vm.flags["SF"] = (ah >> 7) & 1
    vm.flags["ZF"] = (ah >> 6) & 1
    vm.flags["AF"] = (ah >> 4) & 1
    vm.flags["PF"] = (ah >> 2) & 1
    vm.flags["CF"] = ah & 1
    return "SAHF → flags updated from AH"

def op_lahf(vm, opcode):
    ah = (
        (vm.flags["SF"] << 7)
        | (vm.flags["ZF"] << 6)
        | (vm.flags["AF"] << 4)
        | (vm.flags["PF"] << 2)
        | vm.flags["CF"]
    )
    vm.registers["EAX"] = (vm.registers["EAX"] & 0xFFFF00FF) | (ah << 8)
    return "LAHF → AH loaded with flags"

def op_cbw(vm, opcode):
    al = vm.registers["EAX"] & 0xFF
    if al & 0x80:
        vm.registers["EAX"] |= 0xFF00
    else:
        vm.registers["EAX"] &= 0xFFFF00FF
    return "CBW → sign-extended AL into AX"

def op_cwd(vm, opcode):
    ax = vm.registers["EAX"] & 0xFFFF
    if ax & 0x8000:
        vm.registers["EDX"] = 0xFFFF
    else:
        vm.registers["EDX"] = 0
    return "CWD → sign-extended AX into DX"

def op_callf(vm, opcode):
    vm.push(vm.registers["CS"] if "CS" in vm.registers else 0)
    vm.push(vm.registers["EIP"] + 4)
    vm.registers["EIP"] = 0x1000
    return "CALLF → simulated far call"

def op_wait(vm, opcode):
    return "WAIT → simulated FPU wait"

def op_movsb(vm, opcode):
    src = vm.memory[vm.registers["ESI"]]
    vm.memory[vm.registers["EDI"]] = src
    vm.registers["ESI"] += 1
    vm.registers["EDI"] += 1
    return f"MOVSB → copied byte {src:#04x}"

def op_movsd(vm, opcode):
    val = vm.read_mem(vm.registers["ESI"], 4)
    vm.write_mem(vm.registers["EDI"], val, 4)
    vm.registers["ESI"] += 4
    vm.registers["EDI"] += 4
    return f"MOVSD → copied dword {val:#010x}"

def op_cmpsb(vm, opcode):
    a = vm.memory[vm.registers["ESI"]]
    b = vm.memory[vm.registers["EDI"]]
    res = a - b
    vm.update_flags_arithmetic(res, bits=8)
    vm.registers["ESI"] += 1
    vm.registers["EDI"] += 1
    return f"CMPSB → compared {a:#04x} vs {b:#04x}"

def op_cmpsd(vm, opcode):
    a = vm.read_mem(vm.registers["ESI"], 4)
    b = vm.read_mem(vm.registers["EDI"], 4)
    res = a - b
    vm.update_flags_arithmetic(res)
    vm.registers["ESI"] += 4
    vm.registers["EDI"] += 4
    return f"CMPSD → compared {a:#010x} vs {b:#010x}"

def op_lodsb(vm, opcode):
    val = vm.memory[vm.registers["ESI"]]
    vm.registers["EAX"] = (vm.registers["EAX"] & 0xFFFFFF00) | val
    vm.registers["ESI"] += 1
    return f"LODSB → loaded AL={val:#04x}"

def op_lodsd(vm, opcode):
    val = vm.read_mem(vm.registers["ESI"], 4)
    vm.registers["EAX"] = val
    vm.registers["ESI"] += 4
    return f"LODSD → loaded EAX={val:#010x}"

def op_scasb(vm, opcode):
    a = (vm.registers["EAX"] & 0xFF)
    b = vm.memory[vm.registers["EDI"]]
    res = a - b
    vm.update_flags_arithmetic(res, bits=8)
    vm.registers["EDI"] += 1
    return f"SCASB → compared AL={a:#04x} vs {b:#04x}"

def op_scasd(vm, opcode):
    a = vm.registers["EAX"]
    b = vm.read_mem(vm.registers["EDI"], 4)
    res = a - b
    vm.update_flags_arithmetic(res)
    vm.registers["EDI"] += 4
    return f"SCASD → compared EAX={a:#010x} vs {b:#010x}"

def op_xchg_eax_esp(vm, opcode):
    vm.registers["EAX"], vm.registers["ESP"] = vm.registers["ESP"], vm.registers["EAX"]
    return f"XCHG EAX, ESP → EAX={vm.registers['EAX']} ESP={vm.registers['ESP']}"

def op_xchg_eax_ebp(vm, opcode):
    vm.registers["EAX"], vm.registers["EBP"] = vm.registers["EBP"], vm.registers["EAX"]
    return f"XCHG EAX, EBP → EAX={vm.registers['EAX']} EBP={vm.registers['EBP']}"

def op_xchg_eax_esi(vm, opcode):
    vm.registers["EAX"], vm.registers["ESI"] = vm.registers["ESI"], vm.registers["EAX"]
    return f"XCHG EAX, ESI → EAX={vm.registers['EAX']} ESI={vm.registers['ESI']}"

def op_xchg_eax_edi(vm, opcode):
    vm.registers["EAX"], vm.registers["EDI"] = vm.registers["EDI"], vm.registers["EAX"]
    return f"XCHG EAX, EDI → EAX={vm.registers['EAX']} EDI={vm.registers['EDI']}"

def op_cmp_rm32_imm32(vm, opcode):
    val = 1  # placeholder immediate
    res = vm.registers["EAX"] - val
    vm.update_flags_arithmetic(res)
    return f"CMP EAX, {val} → ZF={vm.flags['ZF']}"

def op_cmp_rm32_r32(vm, opcode):
    res = vm.registers["EAX"] - vm.registers["EBX"]
    vm.update_flags_arithmetic(res)
    return f"CMP EAX, EBX → ZF={vm.flags['ZF']}"

def op_mul_rm32(vm, opcode):
    eax = vm.registers["EAX"]
    val = vm.registers["EBX"]
    result = eax * val
    vm.registers["EAX"] = result & 0xFFFFFFFF
    vm.registers["EDX"] = (result >> 32) & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"MUL EAX*EBX → EAX={vm.registers['EAX']} EDX={vm.registers['EDX']}"

def op_imul_rm32(vm, opcode):
    eax = vm.registers["EAX"]
    val = vm.registers["EBX"]
    result = (eax * val) & 0xFFFFFFFFFFFFFFFF
    vm.registers["EAX"] = result & 0xFFFFFFFF
    vm.registers["EDX"] = (result >> 32) & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"IMUL EAX*EBX → EAX={vm.registers['EAX']} EDX={vm.registers['EDX']}"

def op_div_rm32(vm, opcode):
    divisor = vm.registers["EBX"]
    if divisor == 0:
        vm.halted = True
        return "DIV by zero → HALT"
    dividend = (vm.registers["EDX"] << 32) | vm.registers["EAX"]
    quotient = dividend // divisor
    remainder = dividend % divisor
    vm.registers["EAX"] = quotient & 0xFFFFFFFF
    vm.registers["EDX"] = remainder & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"DIV EDX:EAX/EBX → EAX={vm.registers['EAX']} EDX={vm.registers['EDX']}"

def op_idiv_rm32(vm, opcode):
    divisor = vm.registers["EBX"]
    if divisor == 0:
        vm.halted = True
        return "IDIV by zero → HALT"
    dividend = (vm.registers["EDX"] << 32) | vm.registers["EAX"]
    quotient = int(dividend / divisor)
    remainder = dividend % divisor
    vm.registers["EAX"] = quotient & 0xFFFFFFFF
    vm.registers["EDX"] = remainder & 0xFFFFFFFF
    vm.update_flags_arithmetic(vm.registers["EAX"])
    return f"IDIV EDX:EAX/EBX → EAX={vm.registers['EAX']} EDX={vm.registers['EDX']}"


def op_sete_al(vm, opcode):
    vm.registers["EAX"] = (vm.registers["EAX"] & 0xFFFFFF00) | (1 if vm.flags["ZF"] == 1 else 0)
    return f"SETE AL → AL={vm.registers['EAX'] & 0xFF}"

def op_setne_al(vm, opcode):
    vm.registers["EAX"] = (vm.registers["EAX"] & 0xFFFFFF00) | (1 if vm.flags["ZF"] == 0 else 0)
    return f"SETNE AL → AL={vm.registers['EAX'] & 0xFF}"

def op_setl_al(vm, opcode):
    cond = vm.flags["SF"] != vm.flags["OF"]
    vm.registers["EAX"] = (vm.registers["EAX"] & 0xFFFFFF00) | (1 if cond else 0)
    return f"SETL AL → AL={vm.registers['EAX'] & 0xFF}"

def op_setge_al(vm, opcode):
    cond = vm.flags["SF"] == vm.flags["OF"]
    vm.registers["EAX"] = (vm.registers["EAX"] & 0xFFFFFF00) | (1 if cond else 0)
    return f"SETGE AL → AL={vm.registers['EAX'] & 0xFF}"

def op_setg_al(vm, opcode):
    cond = (vm.flags["ZF"] == 0) and (vm.flags["SF"] == vm.flags["OF"])
    vm.registers["EAX"] = (vm.registers["EAX"] & 0xFFFFFF00) | (1 if cond else 0)
    return f"SETG AL → AL={vm.registers['EAX'] & 0xFF}"

def op_setle_al(vm, opcode):
    cond = (vm.flags["ZF"] == 1) or (vm.flags["SF"] != vm.flags["OF"])
    vm.registers["EAX"] = (vm.registers["EAX"] & 0xFFFFFF00) | (1 if cond else 0)
    return f"SETLE AL → AL={vm.registers['EAX'] & 0xFF}"

def op_seto_al(vm, opcode):
    vm.registers["EAX"] = (vm.registers["EAX"] & 0xFFFFFF00) | (1 if vm.flags["OF"] == 1 else 0)
    return f"SETO AL → AL={vm.registers['EAX'] & 0xFF}"

def op_setno_al(vm, opcode):
    vm.registers["EAX"] = (vm.registers["EAX"] & 0xFFFFFF00) | (1 if vm.flags["OF"] == 0 else 0)
    return f"SETNO AL → AL={vm.registers['EAX'] & 0xFF}"

# ------------------------------
# Dispatcher Table
# ------------------------------
OPCODE_EXECUTORS = {
    # Memory / No-ops
    0x00: op_nop,

    # Arithmetic
    0x0B: op_add_eax_ebx,
    0x0C: op_sub_eax_ebx,
    0x0D: op_mul_eax_ebx,
    0x0E: op_imul_eax_ebx,
    0x0F: op_div_eax_ebx,
    0x10: op_idiv_eax_ebx,
    0x11: op_inc_eax,
    0x12: op_dec_eax,

    # Logic
    0x1B: op_and_eax_ebx,
    0x1C: op_or_eax_ebx,
    0x1D: op_xor_eax_ebx,
    0x1E: op_not_eax,
    0x1F: op_shl_eax,
    0x20: op_shr_eax,
    0x21: op_sar_eax,

    # Control Flow
    0x2E: op_jmp_rel8,
    0x2F: op_jmp_rel32,
    0x30: op_call_rel32,
    0x31: op_call_rm32,
    0x32: op_ret,
    0x33: op_ret_imm16,
    0x34: op_int,
    0x35: op_int3,
    0x36: lambda vm, op: op_jcc(vm, op, cond_zf),
    0x37: lambda vm, op: op_jcc(vm, op, cond_nz),
    0x38: lambda vm, op: op_jcc(vm, op, cond_sf),
    0x39: lambda vm, op: op_jcc(vm, op, cond_ns),
    0x3A: lambda vm, op: op_jcc(vm, op, cond_of),
    0x3B: lambda vm, op: op_jcc(vm, op, cond_no),
    0x3C: lambda vm, op: op_jcc(vm, op, cond_cf),
    0x3D: lambda vm, op: op_jcc(vm, op, cond_nc),

    # Terminators
    0x40: op_hlt,
    0x41: op_cmc,
    0x42: op_clc,
    0x43: op_stc,
    0x44: op_cli,
    0x45: op_sti,
    0x46: op_cld,
    0x47: op_std,
    0x48: op_iret,
    0x49: op_loop,
    0x4A: op_loope,
    0x4B: op_loopne,

    # Language Ops (MOV, PUSH, POP, String, Flags, CMP, XCHG, SETcc, etc.)
    0x54: op_mov_imm_eax,
    0x55: op_mov_r32_rm32,
    0x56: op_mov_rm32_r32,
    0x57: op_push_ecx,
    0x58: op_pop_ecx,
    0x59: op_push_edx,
    0x5A: op_pop_edx,
    0x5B: op_push_ebx,
    0x5C: op_pop_ebx,
    0x5D: op_push_eax,
    0x5E: op_pop_eax,
    0x5F: op_push_ebp,
    0x60: op_pop_ebp,
    0x61: op_push_esi,
    0x62: op_pop_esi,
    0x63: op_push_edi,
    0x64: op_pop_edi,

    0x65: op_int,
    0x66: op_int3,
    0x67: op_ret,
    0x68: op_ret_imm16,
    0x69: op_stosb,
    0x6A: op_stosd,
    0x6B: op_test_al_imm8,
    0x6C: op_test_eax_imm32,
    0x6D: op_test_rm8_r8,
    0x6E: op_test_rm32_r32,
    0x6F: op_inc_edi,
    0x70: op_dec_ecx,
    0x71: op_push_rm32,
    0x72: op_pop_rm32,
    0x73: op_call_rel32,
    0x74: op_jmp_rm32,
    0x75: op_jmp_rel8,
    0x76: op_jmp_rel32,
    0x77: op_jne_rel8,
    0x78: op_je_rel8,

    # Conditional jumps (more)
    0x79: op_jl_rel8,
    0x7A: op_jle_rel8,
    0x7B: op_jg_rel8,
    0x7C: op_jge_rel8,
    0x7D: op_jp_rel8,
    0x7E: op_jnp_rel8,
    0x7F: op_jo_rel8,
    0x80: op_jno_rel8,
    0x81: op_js_rel8,
    0x82: op_jns_rel8,
    0x83: op_jbe_rel8,
    0x84: op_ja_rel8,
    0x85: op_jz_rel8,
    0x86: op_jnz_rel8,
    0x87: op_jb_rel8,
    0x88: op_jae_rel8,

    # Flags ops
    0x94: op_pushf,
    0x95: op_popf,
    0x96: op_sahf,
    0x97: op_lahf,
    0x98: op_cbw,
    0x99: op_cwd,
    0x9A: op_callf,
    0x9B: op_wait,
    0x9C: op_movsb,
    0x9D: op_movsd,
    0x9E: op_cmpsb,
    0x9F: op_cmpsd,
    0xA0: op_lodsb,
    0xA1: op_lodsd,
    0xA2: op_scasb,
    0xA3: op_scasd,

    # XCHG / CMP / MUL / DIV
    0xA4: op_xchg_eax_esp,
    0xA5: op_xchg_eax_ebp,
    0xA6: op_xchg_eax_esi,
    0xA7: op_xchg_eax_edi,
    0xA8: op_cmp_rm32_imm32,
    0xA9: op_cmp_rm32_r32,
    0xAA: op_mul_rm32,
    0xAB: op_imul_rm32,
    0xAC: op_div_rm32,
    0xAD: op_idiv_rm32,

    # SETcc
    0xB4: op_sete_al,
    0xB5: op_setne_al,
    0xB6: op_setl_al,
    0xB7: op_setge_al,
    0xB8: op_setg_al,
    0xB9: op_setle_al,
    0xBA: op_seto_al,
    0xBB: op_setno_al,
}

# ------------------------------
# CLI
# ------------------------------
def main():
    parser = argparse.ArgumentParser(description="DGM opcode executor VM", add_help=True)
    parser.add_argument("opcodes", nargs="*", help="Opcodes to execute (e.g., 0x0B 0x5D 0x40)")
    parser.add_argument("--dump-state", action="store_true", help="Dump VM state after execution")
    parser.add_argument("--trace", action="store_true", help="Trace execution step-by-step")
    parser.add_argument("--version", action="store_true", help="Show version and exit")

    args = parser.parse_args()
    if args.version:
        print("executor.py", version_string())
        return

    ex = Executor(trace=args.trace)

    for token in args.opcodes:
        try:
            opcode = int(token, 16)
            result = ex.execute(opcode)
            print(color(f"{token}: {result}", Fore.GREEN))
            if ex.vm.halted:
                break
        except ValueError:
            print(color(f"Invalid opcode: {token}", Fore.RED))

    if args.dump_state:
        print(json.dumps(ex.vm.dump_state(), indent=4))

if __name__ == "__main__":
    main()
