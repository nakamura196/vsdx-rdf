# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['Client']

# %% ../nbs/00_core.ipynb 3
from vsdx import VisioFile
import rdflib
import os
from pprint import pprint
import requests
from .visualize import VisualizeClient
from glob import glob
from typing import Dict, Any, List
import requests
from lxml import etree
from rdflib import Graph

# %% ../nbs/00_core.ipynb 4
class Client:

    @staticmethod
    def convert(input_path: str, output_dir: str, is_download: bool = False) -> None:
        """
        Convert all Visio files found at the specified input path to RDF and visualize them.

        Args:
            input_path (str): A glob pattern to specify which files to process.
            output_dir (str): The directory where output files will be saved.
            is_download (bool): Optional; True to download the files, False by default.
        """
        files = glob(input_path, recursive=True)
        files.sort()

        for filename in files:
            print("Processing:", filename)

            if "佐川" not in filename:
                # continue
                pass

            # output_dir = "/Users/nakamura/Library/CloudStorage/OneDrive-TheUniversityofTokyo/visio/output/" + filename.split('/')[-2] + "/" + filename.split('/')[-1].replace('.vsdx', '')
            output_file_dir = output_dir + "/" + filename.split('/')[-1].replace('.vsdx', '')
            Client.main(filename, output_file_dir , verbose=False, is_download=is_download) # False
            # , page=1 
            # break

    @staticmethod
    def main(path: str, output_dir: str, page: int = -1, verbose: bool = False, is_download: bool = False) -> None:
        """
        Process a single Visio file: parse it, convert it to RDF, and create visualizations.

        Args:
            path (str): The path to the Visio file.
            output_dir (str): The directory to save output files.
            page (int): Optional; specify which page of the Visio file to process, -1 means all pages.
            verbose (bool): Optional; True for detailed output, False by default.
            is_download (bool): Optional; True to download the file, False by default.
        """

        client = Client(path, verbose=verbose, is_download=is_download)

        client.create_nodes_and_edges(page)
        client.convertToRdf()

        paths = client.save(output_dir)

        for path in paths:
                
            if os.path.exists(path) == False:
                continue
            
            output_path = path.replace(".ttl", ".png")

            with open(path, "r") as f:

                text = f.read()

            VisualizeClient.graph_draw_by_kanzaki(text, output_path)
            VisualizeClient.graph_draw_by_kanzaki(text, output_path.replace(".png", ".svg"), gtype="svg")


    def __init__(self, path, verbose=False, is_download=False):
        """
        Initialize the Client with a specific Visio file.

        Args:
            path (str): The path to the Visio file.
            verbose (bool): Optional; True to enable detailed logging, False by default.
            is_download (bool): Optional; True to download the file, False by default.
        """
        self.vis = VisioFile(path)

        self.verbose = verbose
        self.is_download = is_download

    def create_nodes_and_edges(self, page_index: int) -> None:
        """
        Creates nodes and edges based on the provided page index from the visualization pages.
        It collects and organizes data about connections and shapes on each page.

        Args:
        page_index (int): Index of the page to process. If -1, all pages are processed.
        """

        results_by_page: Dict[int, Dict[str, Any]] = {}

        # pages = [vis.pages[1]]

        # Determine the specific pages to process
        pages = self.vis.pages if page_index == -1 else [self.vis.pages[page_index]]


        for page, idx  in zip(pages, range(len(pages))):
            title = page.name
            connects = page.connects
            edges: Dict[str, Dict[str, Any]] = {}

            for connect in connects:

                edge_id = connect.from_id
                if edge_id not in edges:
                    edges[edge_id] = {}

                if connect.from_rel == "BeginX":
                    edges[edge_id]["from"] = connect.to_id
                else:
                    edges[edge_id]["to"] = connect.to_id


            # Process each child shape to create nodes
            nodes: Dict[str, Dict[str, str]] = {}

            for child in page.child_shapes:

                child_id = child.ID
                child_name = child.text.strip()

                shape_name = child.shape_name
                master_page_id = child.master_page_ID


                if child_id in edges:
                        
                    edges[child_id]["name"] = child_name.strip()

                else:

                    if shape_name is None:
                        shape_name = self.determine_shape_name(child, master_page_id)

                    # Add node information
                    node_info = {"name": child_name}

                    if "Circle" in shape_name or "Ellipse" in shape_name:
                        node_info["type"] = "resource"
                    else:
                        node_info["type"] = "literal"

                    nodes[child_id] = {
                        "name": child_name.strip()
                    }

                    nodes[child_id] = node_info


            results_by_page[idx] = {
                "title": title,
                "nodes": nodes,
                "edges": edges
            }

        
        if self.verbose:
            print("----- resultsByPage -----")
            pprint(results_by_page)
            print("-------------------------")

        self.results_by_page = results_by_page

    def determine_shape_name(self, child: Any, master_page_id: str) -> str:
        """
        Determines the shape name based on the child's properties and master page ID.

        Args:
        child (Any): The child shape object.
        master_page_id (str): ID of the master page to help determine the shape.

        Returns:
        str: A string indicating the shape type.
        """
        if master_page_id == "7":
            return "Rectangle"
        elif "Ellipse" in str(child.geometry):
            return "Circle"
        elif "RelLineTo" in str(child.geometry):
            return "Rectangle"
        return "Circle"  # Default case

    def convertToRdf(self):

        prefixes = {
            "foaf": "http://xmlns.com/foaf/0.1/",
            "dcterms": "http://purl.org/dc/terms/",
        }

        resultsByPage = self.results_by_page

        for page in resultsByPage:

            # title = resultsByPage[page]["title"]

            nodes = resultsByPage[page]["nodes"]

            edges = resultsByPage[page]["edges"]

            # RDFグラフを初期化
            g = rdflib.Graph()

            for prefix in prefixes:
                g.bind(prefix, rdflib.Namespace(prefixes[prefix]))

            '''
            # 名前空間の定義
            namespace = rdflib.Namespace("http://example.org/node/")

            g.bind("node", namespace)

            ns_property = rdflib.Namespace("http://example.org/edge/")

            g.bind("edge", ns_property)
            '''

            namespace = rdflib.Namespace("http://example.org/")
            g.bind("ex", namespace)

            uris = {}

            literals = {}

            # ノード（リソース）をグラフに追加
            for node_id, info in nodes.items():

                if info["type"] == "resource":

                    name = info["name"]

                    if name.startswith("http"):
                        node_uri = name

                    elif ":" in name:
                        
                        for prefix in prefixes:
                                
                            if prefix in name:
    
                                name = name.replace(prefix + ":", prefixes[prefix])

                                break

                        node_uri = name

                    else:

                        name = name.replace("\n", "_")

                        node_uri = namespace[name]

                    if node_id not in uris:

                        print(node_uri)

                        if self.is_download:

                            g_extra = self.download(node_uri)

                            if g_extra is not None:
                                    
                                # g += g_extra

                                # 主語がnode_uriのトリプルだけをgに追加
                                for s, p, o in g_extra:
                                    if str(s) == node_uri:
                                        g.add((s, p, o))
                            
                        uris[node_id] = node_uri

                else:
                        
                    literals[node_id] = info["name"]

            ###

            # リレーションシップをグラフに追加
            for rel_id, rel_info in edges.items():

                if "from" not in rel_info:
                    print("from not found")
                    continue

                from_id = rel_info['from']

                if "to" not in rel_info:
                    print("to not found")
                    continue

                to_id = rel_info['to']

                if from_id not in uris:
                    continue

                from_uri = uris[from_id]

                # property_uri = rdflib.URIRef(f"http://schema.org/type") if rel_info['name'] == "タイプ" else rdflib.URIRef(f"http://example.org/title")

                name = rel_info['name'] or "base"

                if name.startswith("http"):
                    property_uri = rdflib.URIRef(name)
                elif ":" in name:
                    for prefix in prefixes:
                        if prefix in name:
                            name = name.replace(prefix + ":", prefixes[prefix])
                            break
                    property_uri = rdflib.URIRef(name)

                else:
                    name = name.replace("\n", "_")
                    property_uri = rdflib.URIRef(namespace[name])

                if to_id in literals:
                    g.add((rdflib.URIRef(from_uri), property_uri, rdflib.Literal(literals[to_id])))

                else:
                    if to_id not in uris:
                        continue

                    to_uri = uris[to_id]

                    g.add((rdflib.URIRef(from_uri), property_uri, rdflib.URIRef(to_uri)))


            # RDFを出力
            # print(g.serialize(format='turtle'))

            self.results_by_page[page]["rdf"] = g # g.serialize(format='turtle').decode()

    def save(self, output_dir):
        """
        Save the RDF data to a file.

        Args:
            output_dir (str): The directory to save the output files.

        Returns:
            List[str]: A list of paths to the saved files.
        """

        resultsByPage = self.results_by_page

        paths = []

        for page in resultsByPage:

            title = resultsByPage[page]["title"]

            g = resultsByPage[page]["rdf"]

            output_path = f"{output_dir}/{title}.ttl"

            paths.append(output_path)

            text = g.serialize(format='turtle')

            if text.strip() == "":
                continue

            os.makedirs(output_dir, exist_ok=True)

            with open(output_path, "w") as f:

                f.write(g.serialize(format='turtle'))

        # print("done")

        return paths

    def download(self, url: str) -> None:
        """
        Download RDF data from a specific URL.

        Args:
            url (str): The URL to download RDF data from.
            
        Returns:
            Graph: An RDF graph object containing the downloaded data.
        """

        # Headers to request RDF/XML format
        headers = {
            'Accept': 'application/rdf+xml'
        }

        # Sending a GET request to the URL
        response = requests.get(url, headers=headers)

        # Checking if the request was successful
        if response.status_code == 200:

            tree = etree.fromstring(response.content)

            # XML Namespace for RDF
            rdf_ns = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
            
            # Remove all nodeID attributes
            for element in tree.xpath('//*[@rdf:nodeID]', namespaces={'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}):
                element.attrib.pop(rdf_ns + 'nodeID')

            modified_xml = etree.tostring(tree, pretty_print=True).decode('utf-8')

            g = Graph()

            g.parse(data=modified_xml, format='xml')

            # g.serialize(destination='output.ttl', format='turtle')

            return g
        else:
            print("Failed to retrieve RDF data. Status code:", response.status_code)

        return None
