from catalog.cadastro import load_cadastro_index


def test_load_cadastro_index_parses_basic_table(tmp_path):
    html = """<!doctype html>
<html>
  <body>
    <table class="waffle">
      <tr><th></th><th>A</th><th>B</th><th>C</th><th></th><th>D</th><th>E</th><th>F</th><th>G</th><th>H</th><th>I</th><th>J</th><th>K</th><th>L</th></tr>
      <tr><th>1</th><td></td><td></td><td>CADASTRO DE PRODUTOS</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
      <tr><th>2</th><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
      <tr>
        <th>3</th>
        <td>CATEGORIA</td>
        <td>CÓDIGO</td>
        <td>DESCRIÇÃO</td>
        <td></td>
        <td>NCM</td>
        <td>IPI</td>
        <td>CEST</td>
        <td>CÓDIGO INMETRO</td>
        <td>TITULO E-COMMERCE</td>
        <td>DESCRIÇÃO E-COMMERCE</td>
        <td>PALAVRAS CHAVE</td>
        <td>DESCRIÇÃO COMERCIAL</td>
        <td>FICHA TÉCNICA</td>
      </tr>
      <tr>
        <th>4</th>
        <td>LAMPADA</td>
        <td>1580</td>
        <td>LAMP LED A60 BULBO 7W BIVOLT 3000K E27</td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td>LAMP LED A60 BULBO 7W BIVOLT 3000K E27</td>
        <td>Lâmpada LED Bulbo 7W A-60 Bivolt 3000K E27</td>
        <td></td>
        <td>Descrição comercial</td>
        <td>CÓDIGO: 1580 | POTÊNCIA: 7W</td>
      </tr>
    </table>
  </body>
</html>
"""
    html_path = tmp_path / "CADASTRO.html"
    html_path.write_text(html, encoding="utf-8")

    index = load_cadastro_index(str(html_path))
    assert "1580" in index
    row = index["1580"]
    assert row["code"] == "1580"
    assert row["category"] == "LAMPADA"
    assert row["name"] == "LAMP LED A60 BULBO 7W BIVOLT 3000K E27"
    assert row["description"] == "Lâmpada LED Bulbo 7W A-60 Bivolt 3000K E27"
    assert row["specs"] == "CÓDIGO: 1580 | POTÊNCIA: 7W"
