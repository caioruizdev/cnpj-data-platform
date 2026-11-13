import io

from cnpj_pipeline.utf8 import converter_para_utf8


def test_converte_latin1_para_utf8_e_conta_linhas(tmp_path):
    origem = io.BytesIO('"1";"AÇÚCAR LTDA"\n"2";"JOSÉ"\n'.encode("latin-1"))
    destino = tmp_path / "saida.csv"

    linhas = converter_para_utf8(origem, destino)

    assert linhas == 2
    assert destino.read_text(encoding="utf-8") == '"1";"AÇÚCAR LTDA"\n"2";"JOSÉ"\n'


def test_conta_ultima_linha_sem_quebra_final(tmp_path):
    origem = io.BytesIO(b'"1";"A"\n"2";"B"')
    assert converter_para_utf8(origem, tmp_path / "saida.csv") == 2


def test_blocos_pequenos_nao_corrompem_acentos(tmp_path):
    texto = '"1";"AÇÚCAR"\n' * 50
    origem = io.BytesIO(texto.encode("latin-1"))
    destino = tmp_path / "saida.csv"

    linhas = converter_para_utf8(origem, destino, tamanho_bloco=7)

    assert linhas == 50
    assert destino.read_text(encoding="utf-8") == texto


def test_arquivo_vazio(tmp_path):
    assert converter_para_utf8(io.BytesIO(b""), tmp_path / "saida.csv") == 0
