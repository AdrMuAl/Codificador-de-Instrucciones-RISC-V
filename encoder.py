import sys
import re


# 12 instrucciones requeridas
INSTRUCCIONES = {
    "add":  {"formato": "R", "opcode": 0b0110011, "funct3": 0b000, "funct7": 0b0000000},
    "sub":  {"formato": "R", "opcode": 0b0110011, "funct3": 0b000, "funct7": 0b0100000},
    "and":  {"formato": "R", "opcode": 0b0110011, "funct3": 0b111, "funct7": 0b0000000},
    "or":   {"formato": "R", "opcode": 0b0110011, "funct3": 0b110, "funct7": 0b0000000},

    "addi": {"formato": "I", "opcode": 0b0010011, "funct3": 0b000},
    "andi": {"formato": "I", "opcode": 0b0010011, "funct3": 0b111},

    "lw":   {"formato": "I", "opcode": 0b0000011, "funct3": 0b010},
    "lb":   {"formato": "I", "opcode": 0b0000011, "funct3": 0b000},

    "sw":   {"formato": "S", "opcode": 0b0100011, "funct3": 0b010},
    "sb":   {"formato": "S", "opcode": 0b0100011, "funct3": 0b000},

    "beq":  {"formato": "B", "opcode": 0b1100011, "funct3": 0b000},
    "bne":  {"formato": "B", "opcode": 0b1100011, "funct3": 0b001},
}


def parsear_registro(texto):
    texto = texto.strip().lower()

    coincidencia = re.fullmatch(r"x(\d+)", texto)

    if not coincidencia:
        raise ValueError(f"Registro inválido: {texto}")

    numero = int(coincidencia.group(1))

    if numero < 0 or numero > 31:
        raise ValueError(f"Registro fuera de rango: {texto}")

    return numero


def parsear_inmediato(texto):
    try:
        return int(texto.strip())
    except ValueError:
        raise ValueError(f"Inmediato inválido: {texto}")


def parsear_memoria(texto):
    coincidencia = re.fullmatch(
        r"\s*([+-]?\d+)\s*\(\s*(x\d+)\s*\)\s*",
        texto,
        re.IGNORECASE
    )

    if not coincidencia:
        raise ValueError(f"Operando de memoria inválido: {texto}")

    inmediato = parsear_inmediato(coincidencia.group(1))
    registro = parsear_registro(coincidencia.group(2))

    return inmediato, registro


def parsear_instruccion(texto):
    texto = texto.strip().lower()

    partes = texto.split(maxsplit=1)

    if len(partes) != 2:
        raise ValueError("La instrucción debe incluir mnemónico y operandos")

    mnemonico = partes[0]
    texto_operandos = partes[1]

    if mnemonico not in INSTRUCCIONES:
        raise ValueError(f"Instrucción no soportada: {mnemonico}")

    operandos = [op.strip() for op in texto_operandos.split(",")]

    # Formato R: add rd, rs1, rs2
    if mnemonico in {"add", "sub", "and", "or"}:
        if len(operandos) != 3:
            raise ValueError("La instrucción tipo R requiere 3 registros")

        return {
            "mnemonico": mnemonico,
            "formato": "R",
            "rd": parsear_registro(operandos[0]),
            "rs1": parsear_registro(operandos[1]),
            "rs2": parsear_registro(operandos[2]),
        }

    # Formato I aritmético: addi rd, rs1, inmediato
    if mnemonico in {"addi", "andi"}:
        if len(operandos) != 3:
            raise ValueError("La instrucción requiere 3 operandos")

        return {
            "mnemonico": mnemonico,
            "formato": "I",
            "rd": parsear_registro(operandos[0]),
            "rs1": parsear_registro(operandos[1]),
            "inmediato": parsear_inmediato(operandos[2]),
        }

    # Formato I de carga: lw rd, inmediato(rs1)
    if mnemonico in {"lw", "lb"}:
        if len(operandos) != 2:
            raise ValueError("La instrucción de carga requiere 2 operandos")

        inmediato, rs1 = parsear_memoria(operandos[1])

        return {
            "mnemonico": mnemonico,
            "formato": "I",
            "rd": parsear_registro(operandos[0]),
            "rs1": rs1,
            "inmediato": inmediato,
        }

    # Formato S: sw rs2, inmediato(rs1)
    if mnemonico in {"sw", "sb"}:
        if len(operandos) != 2:
            raise ValueError("La instrucción de almacenamiento requiere 2 operandos")

        inmediato, rs1 = parsear_memoria(operandos[1])

        return {
            "mnemonico": mnemonico,
            "formato": "S",
            "rs1": rs1,
            "rs2": parsear_registro(operandos[0]),
            "inmediato": inmediato,
        }

    # Formato B: beq rs1, rs2, desplazamiento
    if mnemonico in {"beq", "bne"}:
        if len(operandos) != 3:
            raise ValueError("La instrucción de salto requiere 3 operandos")

        return {
            "mnemonico": mnemonico,
            "formato": "B",
            "rs1": parsear_registro(operandos[0]),
            "rs2": parsear_registro(operandos[1]),
            "inmediato": parsear_inmediato(operandos[2]),
        }


def validar_inmediato_12(inmediato):
    if inmediato < -2048 or inmediato > 2047:
        raise ValueError(
            f"Inmediato fuera de rango: {inmediato}. "
            "Debe estar entre -2048 y 2047"
        )


def codificar_r(instruccion):
    datos = INSTRUCCIONES[instruccion["mnemonico"]]

    funct7 = datos["funct7"]
    funct3 = datos["funct3"]
    opcode = datos["opcode"]

    rd = instruccion["rd"]
    rs1 = instruccion["rs1"]
    rs2 = instruccion["rs2"]

    codigo = (
        (funct7 << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | (rd << 7)
        | opcode
    )

    return codigo


def codificar_i(instruccion):
    datos = INSTRUCCIONES[instruccion["mnemonico"]]

    funct3 = datos["funct3"]
    opcode = datos["opcode"]

    rd = instruccion["rd"]
    rs1 = instruccion["rs1"]
    inmediato = instruccion["inmediato"]

    validar_inmediato_12(inmediato)

    # Se conservan únicamente los 12 bits del inmediato.
    # Esto permite representar correctamente números negativos
    # en complemento a dos.
    inmediato_12 = inmediato & 0xFFF

    codigo = (
        (inmediato_12 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | (rd << 7)
        | opcode
    )

    return codigo

def codificar_s(instruccion):
    datos = INSTRUCCIONES[instruccion["mnemonico"]]

    funct3 = datos["funct3"]
    opcode = datos["opcode"]

    rs1 = instruccion["rs1"]
    rs2 = instruccion["rs2"]
    inmediato = instruccion["inmediato"]

    validar_inmediato_12(inmediato)

    inmediato_12 = inmediato & 0xFFF

    inmediato_bajo = inmediato_12 & 0x1F
    inmediato_alto = (inmediato_12 >> 5) & 0x7F

    codigo = (
        (inmediato_alto << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | (inmediato_bajo << 7)
        | opcode
    )

    return codigo

def validar_inmediato_b(inmediato):
    if inmediato < -4096 or inmediato > 4094:
        raise ValueError(
            f"Desplazamiento fuera de rango: {inmediato}. "
            "Debe estar entre -4096 y 4094"
        )

    if inmediato % 2 != 0:
        raise ValueError(
            f"Desplazamiento inválido: {inmediato}. "
            "Debe ser múltiplo de 2"
        )

def codificar_b(instruccion):
    datos = INSTRUCCIONES[instruccion["mnemonico"]]

    funct3 = datos["funct3"]
    opcode = datos["opcode"]

    rs1 = instruccion["rs1"]
    rs2 = instruccion["rs2"]
    inmediato = instruccion["inmediato"]

    validar_inmediato_b(inmediato)

    inmediato_13 = inmediato & 0x1FFF

    bit_12 = (inmediato_13 >> 12) & 0x1
    bits_10_5 = (inmediato_13 >> 5) & 0x3F
    bits_4_1 = (inmediato_13 >> 1) & 0xF
    bit_11 = (inmediato_13 >> 11) & 0x1

    codigo = (
        (bit_12 << 31)
        | (bits_10_5 << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | (bits_4_1 << 8)
        | (bit_11 << 7)
        | opcode
    )

    return codigo

def codificar_instruccion(instruccion):
    formato = instruccion["formato"]

    if formato == "R":
        return codificar_r(instruccion)

    if formato == "I":
        return codificar_i(instruccion)

    if formato == "S":
        return codificar_s(instruccion)

    if formato == "B":
        return codificar_b(instruccion)

    raise ValueError(f"Formato no soportado: {formato}")

def main():
    if len(sys.argv) != 2:
        print('Uso: ./run.sh "<instruccion>"')
        sys.exit(1)

    try:
        instruccion = parsear_instruccion(sys.argv[1])

        codigo = codificar_instruccion(instruccion)

        binario = f"{codigo:032b}"
        hexadecimal = f"0x{codigo:08X}"

        print(f"Instrucción: {instruccion['mnemonico']}")
        print(f"Formato: {instruccion['formato']}")
        
        print(f"Binario: {binario}")
        print(f"HEX: {hexadecimal}")

    except ValueError as error:
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()