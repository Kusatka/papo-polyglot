"""Проверяет RESP-файлы до запуска Docker: CRLF и длины строк в байтах."""
from pathlib import Path


def validate(data):
    pos, commands = 0, 0

    def line():
        nonlocal pos
        end = data.find(b'\r\n', pos)
        if end < 0:
            raise ValueError(f'Нет CRLF на смещении {pos}')
        value, pos = data[pos:end], end + 2
        return value

    while pos < len(data):
        header = line()
        if not header.startswith(b'*'):
            raise ValueError('Ожидался массив RESP')
        count = int(header[1:])
        if count < 1:
            raise ValueError('Команда не может быть пустой')
        for _ in range(count):
            header = line()
            if not header.startswith(b'$'):
                raise ValueError('Ожидалась bulk string')
            length = int(header[1:])
            if length < 0 or data[pos + length:pos + length + 2] != b'\r\n':
                raise ValueError(f'Неверная длина строки на смещении {pos}')
            pos += length + 2
        commands += 1
    return commands


if __name__ == '__main__':
    for path in Path(__file__).resolve().parents[2].rglob('*.resp'):
        print(path.name, validate(path.read_bytes()), 'commands: valid')
    try:
        validate(b'*1\n$4\nPING\n')
    except ValueError:
        print('Corrupted LF-only protocol correctly rejected')
    else:
        raise AssertionError('Parser accepted damaged RESP')
