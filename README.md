# Codificador de Instrucciones RISC-V RV32I

## Preparación del entorno

El proyecto está desarrollado en Python 3 y utiliza Bash para ejecutar el archivo `run.sh`.

No requiere dependencias externas de Python.

En Ubuntu o WSL, para instalar el toolchain utilizado en la validación se puede ejecutar:

```bash
sudo apt update
sudo apt install gcc-riscv64-unknown-elf binutils-riscv64-unknown-elf
```

Se puede verificar la instalación con:

```bash
riscv64-unknown-elf-as --version
riscv64-unknown-elf-objdump --version
```

Si `run.sh` no tiene permisos de ejecución, se pueden asignar con:

```bash
chmod +x run.sh
```

## Ejecución

El programa se ejecuta mediante:

```bash
./run.sh "<instruccion>"
```

Por ejemplo:

```bash
./run.sh "add x5, x6, x7"
```

## Pruebas de verificación

Los 36 casos utilizados para la validación se encuentran en:

`validacion/casos_prueba.txt`

Para ejecutar la comparación contra el toolchain de RISC-V:

```bash
python3 validacion/validar.py
```

Los resultados obtenidos se encuentran en:

`validacion/resultados.txt`
