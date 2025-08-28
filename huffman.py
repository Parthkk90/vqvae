import heapq
from collections import defaultdict

class HuffmanNode:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq

def build_freq_map(data):
    freq_map = defaultdict(int)
    for item in data:
        freq_map[item] += 1
    return freq_map

def build_huffman_tree(freq_map):
    priority_queue = [HuffmanNode(char, freq) for char, freq in freq_map.items()]
    heapq.heapify(priority_queue)
    while len(priority_queue) > 1:
        left = heapq.heappop(priority_queue)
        right = heapq.heappop(priority_queue)
        merged = HuffmanNode(None, left.freq + right.freq)
        merged.left = left
        merged.right = right
        heapq.heappush(priority_queue, merged)
    if not priority_queue:
        return None
    return priority_queue[0]

def _build_huffman_codes_recursive(node, current_code, huffman_codes):
    if node is None:
        return
    if node.char is not None:
        huffman_codes[node.char] = current_code
        return
    _build_huffman_codes_recursive(node.left, current_code + "0", huffman_codes)
    _build_huffman_codes_recursive(node.right, current_code + "1", huffman_codes)

def build_huffman_codes(huffman_tree):
    huffman_codes = {}
    _build_huffman_codes_recursive(huffman_tree, "", huffman_codes)
    return huffman_codes

def huffman_encoding(data, huffman_codes):
    return "".join(huffman_codes[value] for value in data)

def huffman_decoding(encoded_data, huffman_tree):
    if huffman_tree is None or (huffman_tree.left is None and huffman_tree.right is None):
        return [huffman_tree.char] * len(encoded_data) if huffman_tree else []

    decoded_output = []
    current_node = huffman_tree
    for bit in encoded_data:
        current_node = current_node.left if bit == '0' else current_node.right
        if current_node.left is None and current_node.right is None:
            decoded_output.append(current_node.char)
            current_node = huffman_tree
    return decoded_output