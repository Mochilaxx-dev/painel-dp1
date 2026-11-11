#!/usr/bin/env python3
"""Gera o ícone do Painel DP"""

import os

try:
    from PIL import Image, ImageDraw, ImageFont

    # Criar imagem
    img = Image.new('RGB', (256, 256), color=(36, 87, 214))
    draw = ImageDraw.Draw(img)

    # Cores
    cores = [
        (255, 107, 94),   # Vermelho (atrasadas)
        (240, 164, 60),   # Laranja (hoje)
        (111, 207, 151),  # Verde (próximos dias)
    ]

    # Cards no topo
    for i, cor in enumerate(cores):
        x = 40 + i * 60
        y = 50
        draw.rectangle([x, y, x+50, y+40], fill=cor)

    # Barras de lista
    lista_cor = (200, 200, 200)
    for i, dy in enumerate([110, 130, 150]):
        draw.rectangle([40, dy, 190, dy+10], fill=lista_cor)

    # Texto DP
    try:
        fonte = ImageFont.truetype("arial.ttf", 60)
    except:
        fonte = ImageFont.load_default()

    draw.text((80, 180), "DP", font=fonte, fill=(255, 255, 255))

    # Salvar como ICO
    ico_path = os.path.join(os.path.dirname(__file__), 'painel.ico')
    img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])

    print(f"✓ Ícone criado: {ico_path}")

except ImportError:
    print("PIL não instalado, mas tudo bem - vamos criar o atalho mesmo assim")
