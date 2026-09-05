import os
import re
import subprocess
import tempfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_CASOS = Path(__file__).resolve().parent / "casos_prueba.txt"

ASSEMBLER = "riscv64-unknown-elf-as"
OBJDUMP = "riscv64-unknown-elf-objdump"


def preparar_instruccion_toolchain(instruccion):
    partes = instruccion.split(maxsplit=1)
    mnemonico = partes[0]

    if mnemonico not in {"beq", "bne"}:
        return instruccion

    operandos = [op.strip() for op in partes[1].split(",")]
    desplazamiento = int(operandos[2])

    if desplazamiento == 0:
        destino = "."
    elif desplazamiento > 0:
        destino = f".+{desplazamiento}"
    else:
        destino = f".{desplazamiento}"

    return f"{mnemonico} {operandos[0]}, {operandos[1]}, {destino}"


def obtener_hex_toolchain(instruccion):
    instruccion_asm = preparar_instruccion_toolchain(instruccion)

    codigo_asm = (
        ".text\n"
        ".globl _start\n"
        "_start:\n"
        f"    {instruccion_asm}\n"
    )

    with tempfile.TemporaryDirectory() as temp:
        archivo_s = Path(temp) / "prueba.s"
        archivo_o = Path(temp) / "prueba.o"

        archivo_s.write_text(codigo_asm)

        subprocess.run(
            [
                ASSEMBLER,
                "-march=rv32i",
                "-mabi=ilp32",
                "-o",
                str(archivo_o),
                str(archivo_s),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        resultado = subprocess.run(
            [
                OBJDUMP,
                "-d",
                "-M",
                "numeric,no-aliases",
                str(archivo_o),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        coincidencia = re.search(
            r"^\s*0:\s+([0-9a-fA-F]{8})\s",
            resultado.stdout,
            re.MULTILINE,
        )

        if not coincidencia:
            raise RuntimeError(
                f"No se pudo obtener la codificación de objdump para: {instruccion}"
            )

        return "0x" + coincidencia.group(1).upper()


def obtener_hex_modelo(instruccion):
    resultado = subprocess.run(
        [str(RAIZ / "run.sh"), instruccion],
        cwd=RAIZ,
        check=True,
        capture_output=True,
        text=True,
    )

    coincidencia = re.search(
        r"HEX:\s*(0x[0-9A-Fa-f]{8})",
        resultado.stdout
    )

    if not coincidencia:
        raise RuntimeError(
            f"No se encontró la salida HEX del modelo para: {instruccion}"
        )

    return coincidencia.group(1).upper()


def cargar_casos():
    casos = []

    for linea in ARCHIVO_CASOS.read_text().splitlines():
        linea = linea.strip()

        if not linea or linea.startswith("#"):
            continue

        instruccion, escenario = linea.split(";", maxsplit=1)

        casos.append(
            (instruccion.strip(), escenario.strip())
        )

    return casos


def main():
    casos = cargar_casos()

    correctos = 0

    print(
        f"{'#':<4}"
        f"{'Instrucción':<30}"
        f"{'Modelo':<12}"
        f"{'Objdump':<12}"
        f"Resultado"
    )
    print("-" * 80)

    for numero, (instruccion, escenario) in enumerate(casos, start=1):
        try:
            modelo = obtener_hex_modelo(instruccion)
            oficial = obtener_hex_toolchain(instruccion)

            coincide = modelo.lower() == oficial.lower()

            if coincide:
                resultado = "PASS"
                correctos += 1
            else:
                resultado = "FAIL"

            print(
                f"{numero:<4}"
                f"{instruccion:<30}"
                f"{modelo:<12}"
                f"{oficial:<12}"
                f"{resultado}"
            )

        except Exception as error:
            print(
                f"{numero:<4}"
                f"{instruccion:<30}"
                f"{'-':<12}"
                f"{'-':<12}"
                f"ERROR: {error}"
            )

    print("-" * 80)
    print(f"Resultado final: {correctos}/{len(casos)} casos correctos")


if __name__ == "__main__":
    main()