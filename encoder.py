import sys

def main():
    if len(sys.argv) != 2:
        print('Uso: ./run.sh "<instruccion>"')
        sys.exit(1)

    instruccion = sys.argv[1]

    print(f"Instrucción recibida: {instruccion}")


if __name__ == "__main__":
    main()