"""Gera o painel.ico (preto e cinza, estilo "lista de tarefas") sem bibliotecas externas."""
import os
import struct

TAM = 64


def pixel(x, y):
    # fundo arredondado preto
    r = 12
    cx = min(max(x, r), TAM - 1 - r)
    cy = min(max(y, r), TAM - 1 - r)
    if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
        return (0, 0, 0, 0)
    cor = (24, 24, 24, 255)
    # três linhas: caixinha + barra
    for i, linha_y in enumerate((16, 30, 44)):
        if linha_y <= y < linha_y + 8:
            if 12 <= x < 20:
                borda = x in (12, 19) or y in (linha_y, linha_y + 7)
                if i == 0 and 14 <= x <= 17 and linha_y + 2 <= y <= linha_y + 5:
                    return (110, 207, 151, 255)  # primeira tarefa concluída (verde)
                if borda:
                    return (200, 200, 200, 255)
            if 26 <= x < (52 if i != 1 else 44) and linha_y + 2 <= y < linha_y + 6:
                return (170, 170, 170, 255) if i else (230, 230, 230, 255)
    return cor


def gerar(caminho):
    linhas = []
    for y in range(TAM - 1, -1, -1):  # BMP é de baixo para cima
        for x in range(TAM):
            r, g, b, a = pixel(x, y)
            linhas.append(struct.pack('BBBB', b, g, r, a))
    xor = b''.join(linhas)
    mascara = b'\x00' * ((TAM // 8) * TAM)
    cab = struct.pack('<IiiHHIIiiII', 40, TAM, TAM * 2, 1, 32, 0, len(xor) + len(mascara), 0, 0, 0, 0)
    img = cab + xor + mascara
    ico = struct.pack('<HHH', 0, 1, 1) + struct.pack('<BBBBHHII', TAM, TAM, 0, 0, 1, 32, len(img), 22) + img
    with open(caminho, 'wb') as f:
        f.write(ico)


if __name__ == '__main__':
    gerar(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'painel.ico'))
