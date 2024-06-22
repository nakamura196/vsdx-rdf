# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_visualize.ipynb.

# %% auto 0
__all__ = ['VisualizeClient']

# %% ../nbs/01_visualize.ipynb 3
import os
import requests

# %% ../nbs/01_visualize.ipynb 4
class VisualizeClient:
    @staticmethod
    def graph_draw_by_kanzaki(text, output_path, gtype="png"):
        """
        指定されたRDF/Turtle形式のテキストデータをグラフとして可視化し、結果をPNGファイルとして保存します。
        
        Args:
            text (str): RDFデータを表すテキスト、Turtle形式。
            output_path (str): 生成されたPNGファイルの保存先パス。
        """

        # POSTリクエストに必要なデータ
        url = "https://www.kanzaki.com/works/2009/pub/graph-draw"

        data = {
            "RDF": text,
            "rtype": "turtle",
            "gtype": gtype, # "png",
            "rankdir": "lr",
            "qname": "on",
        }

        # POSTリクエストを送信
        response = requests.post(url, data=data)

        if gtype == "svg":
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            # 応答をSVGファイルとして保存
            with open(output_path, 'w') as f:
                f.write(response.text)

        # 応答がPNG画像でない場合、内容を確認
        elif response.headers['Content-Type'] != 'image/png':
            print("応答はPNG画像ではありません。")
            # print(response.text[:500])  # 最初の500文字を表示 # [:500]
        
        else:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            # 応答をPNGファイルとして保存
            with open(output_path, 'wb') as f:
                f.write(response.content)

