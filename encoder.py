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

def imprimir_tabla_campos(campos):
    print()
    print("Campos de la instrucción:")
    print("-" * 95)

    print(
        f"{'Campo':<12}"
        f"{'Bits':<10}"
        f"{'Binario':<16}"
        f"{'Decimal':<10}"
        f"Descripción"
    )

    print("-" * 95)

    for campo in campos:
        nombre = campo["nombre"]
        bits = campo["bits"]
        valor = campo["valor"]
        ancho = campo["ancho"]
        decimal = campo["decimal"]
        descripcion = campo["descripcion"]

        binario = f"{valor:0{ancho}b}"

        print(
            f"{nombre:<12}"
            f"{bits:<10}"
            f"{binario:<16}"
            f"{decimal:<10}"
            f"{descripcion}"
        )

    print("-" * 95)

def obtener_campos_r(instruccion):
    datos = INSTRUCCIONES[instruccion["mnemonico"]]
    mnemonico = instruccion["mnemonico"]

    return [
        {
            "nombre": "funct7",
            "bits": "31-25",
            "valor": datos["funct7"],
            "ancho": 7,
            "decimal": datos["funct7"],
            "descripcion": f"Junto con funct3 identifica la operación {mnemonico}"
        },
        {
            "nombre": "rs2",
            "bits": "24-20",
            "valor": instruccion["rs2"],
            "ancho": 5,
            "decimal": instruccion["rs2"],
            "descripcion": f"Segundo registro fuente: x{instruccion['rs2']}"
        },
        {
            "nombre": "rs1",
            "bits": "19-15",
            "valor": instruccion["rs1"],
            "ancho": 5,
            "decimal": instruccion["rs1"],
            "descripcion": f"Primer registro fuente: x{instruccion['rs1']}"
        },
        {
            "nombre": "funct3",
            "bits": "14-12",
            "valor": datos["funct3"],
            "ancho": 3,
            "decimal": datos["funct3"],
            "descripcion": f"Junto con funct7 identifica la operación {mnemonico}"
        },
        {
            "nombre": "rd",
            "bits": "11-7",
            "valor": instruccion["rd"],
            "ancho": 5,
            "decimal": instruccion["rd"],
            "descripcion": f"Registro destino: x{instruccion['rd']}"
        },
        {
            "nombre": "opcode",
            "bits": "6-0",
            "valor": datos["opcode"],
            "ancho": 7,
            "decimal": datos["opcode"],
            "descripcion": "Identifica el tipo general de operación"
        }
    ]

def obtener_campos_i(instruccion):
    datos = INSTRUCCIONES[instruccion["mnemonico"]]
    mnemonico = instruccion["mnemonico"]

    inmediato = instruccion["inmediato"]
    inmediato_12 = inmediato & 0xFFF

    if mnemonico in {"lw", "lb"}:
        descripcion_inmediato = (
            f"Desplazamiento respecto a x{instruccion['rs1']}: "
            f"{inmediato}"
        )
        descripcion_rs1 = (
            f"Registro base de la dirección: x{instruccion['rs1']}"
        )
        descripcion_rd = (
            f"Registro donde se carga el dato: x{instruccion['rd']}"
        )
    else:
        descripcion_inmediato = (
            f"Valor inmediato usado por {mnemonico}: {inmediato}"
        )
        descripcion_rs1 = (
            f"Registro fuente: x{instruccion['rs1']}"
        )
        descripcion_rd = (
            f"Registro destino: x{instruccion['rd']}"
        )

    return [
        {
            "nombre": "imm[11:0]",
            "bits": "31-20",
            "valor": inmediato_12,
            "ancho": 12,
            "decimal": inmediato,
            "descripcion": descripcion_inmediato
        },
        {
            "nombre": "rs1",
            "bits": "19-15",
            "valor": instruccion["rs1"],
            "ancho": 5,
            "decimal": instruccion["rs1"],
            "descripcion": descripcion_rs1
        },
        {
            "nombre": "funct3",
            "bits": "14-12",
            "valor": datos["funct3"],
            "ancho": 3,
            "decimal": datos["funct3"],
            "descripcion": f"Identifica la operación {mnemonico}"
        },
        {
            "nombre": "rd",
            "bits": "11-7",
            "valor": instruccion["rd"],
            "ancho": 5,
            "decimal": instruccion["rd"],
            "descripcion": descripcion_rd
        },
        {
            "nombre": "opcode",
            "bits": "6-0",
            "valor": datos["opcode"],
            "ancho": 7,
            "decimal": datos["opcode"],
            "descripcion": "Identifica el tipo general de operación"
        }
    ]

def obtener_campos_s(instruccion):
    datos = INSTRUCCIONES[instruccion["mnemonico"]]

    inmediato = instruccion["inmediato"]
    inmediato_12 = inmediato & 0xFFF

    inmediato_alto = (inmediato_12 >> 5) & 0x7F
    inmediato_bajo = inmediato_12 & 0x1F

    return [
        {
            "nombre": "imm[11:5]",
            "bits": "31-25",
            "valor": inmediato_alto,
            "ancho": 7,
            "decimal": inmediato_alto,
            "descripcion": f"Parte alta del desplazamiento {inmediato}"
        },
        {
            "nombre": "rs2",
            "bits": "24-20",
            "valor": instruccion["rs2"],
            "ancho": 5,
            "decimal": instruccion["rs2"],
            "descripcion": f"Registro que contiene el dato a guardar: x{instruccion['rs2']}"
        },
        {
            "nombre": "rs1",
            "bits": "19-15",
            "valor": instruccion["rs1"],
            "ancho": 5,
            "decimal": instruccion["rs1"],
            "descripcion": f"Registro base de la dirección: x{instruccion['rs1']}"
        },
        {
            "nombre": "funct3",
            "bits": "14-12",
            "valor": datos["funct3"],
            "ancho": 3,
            "decimal": datos["funct3"],
            "descripcion": f"Identifica la operación {instruccion['mnemonico']}"
        },
        {
            "nombre": "imm[4:0]",
            "bits": "11-7",
            "valor": inmediato_bajo,
            "ancho": 5,
            "decimal": inmediato_bajo,
            "descripcion": f"Parte baja del desplazamiento {inmediato}"
        },
        {
            "nombre": "opcode",
            "bits": "6-0",
            "valor": datos["opcode"],
            "ancho": 7,
            "decimal": datos["opcode"],
            "descripcion": "Identifica una instrucción de almacenamiento"
        }
    ]

def obtener_campos_b(instruccion):
    datos = INSTRUCCIONES[instruccion["mnemonico"]]

    inmediato = instruccion["inmediato"]
    inmediato_13 = inmediato & 0x1FFF

    bit_12 = (inmediato_13 >> 12) & 0x1
    bits_10_5 = (inmediato_13 >> 5) & 0x3F
    bits_4_1 = (inmediato_13 >> 1) & 0xF
    bit_11 = (inmediato_13 >> 11) & 0x1

    return [
        {
            "nombre": "imm[12]",
            "bits": "31",
            "valor": bit_12,
            "ancho": 1,
            "decimal": bit_12,
            "descripcion": f"Bit 12 del desplazamiento {inmediato}"
        },
        {
            "nombre": "imm[10:5]",
            "bits": "30-25",
            "valor": bits_10_5,
            "ancho": 6,
            "decimal": bits_10_5,
            "descripcion": f"Bits 10 a 5 del desplazamiento {inmediato}"
        },
        {
            "nombre": "rs2",
            "bits": "24-20",
            "valor": instruccion["rs2"],
            "ancho": 5,
            "decimal": instruccion["rs2"],
            "descripcion": f"Segundo registro a comparar: x{instruccion['rs2']}"
        },
        {
            "nombre": "rs1",
            "bits": "19-15",
            "valor": instruccion["rs1"],
            "ancho": 5,
            "decimal": instruccion["rs1"],
            "descripcion": f"Primer registro a comparar: x{instruccion['rs1']}"
        },
        {
            "nombre": "funct3",
            "bits": "14-12",
            "valor": datos["funct3"],
            "ancho": 3,
            "decimal": datos["funct3"],
            "descripcion": f"Identifica la condición {instruccion['mnemonico']}"
        },
        {
            "nombre": "imm[4:1]",
            "bits": "11-8",
            "valor": bits_4_1,
            "ancho": 4,
            "decimal": bits_4_1,
            "descripcion": f"Bits 4 a 1 del desplazamiento {inmediato}"
        },
        {
            "nombre": "imm[11]",
            "bits": "7",
            "valor": bit_11,
            "ancho": 1,
            "decimal": bit_11,
            "descripcion": f"Bit 11 del desplazamiento {inmediato}"
        },
        {
            "nombre": "opcode",
            "bits": "6-0",
            "valor": datos["opcode"],
            "ancho": 7,
            "decimal": datos["opcode"],
            "descripcion": "Identifica una instrucción de salto condicional"
        }
    ]

def mostrar_campos(instruccion):
    formato = instruccion["formato"]

    if formato == "R":
        campos = obtener_campos_r(instruccion)
    elif formato == "I":
        campos = obtener_campos_i(instruccion)
    elif formato == "S":
        campos = obtener_campos_s(instruccion)
    elif formato == "B":
        campos = obtener_campos_b(instruccion)
    else:
        raise ValueError(f"Formato no soportado: {formato}")

    imprimir_tabla_campos(campos)


def main():
    if len(sys.argv) != 2:
        print('Uso: ./run.sh "<instruccion>"')
        sys.exit(1)

    try:
        texto_original = sys.argv[1]
        instruccion = parsear_instruccion(sys.argv[1])

        codigo = codificar_instruccion(instruccion)

        binario = f"{codigo:032b}"
        hexadecimal = f"0x{codigo:08X}"

        print()
        print(f"Instrucción: {texto_original}")
        print(f"Formato: {instruccion['formato']}")
        print(f"Binario: {binario}")

        mostrar_campos(instruccion)

        print(f"HEX: {hexadecimal}")
    except ValueError as error:
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()