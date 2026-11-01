"""Lossless editing of the binding lists in a ZMK keymap."""
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path


def digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def masked(source):
    def blank(match):
        return ''.join('\n' if c == '\n' else ' ' for c in match.group())
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"', blank, source, flags=re.S)


def closing(text, start, left='{', right='}'):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == left:
            depth += 1
        elif text[i] == right:
            depth -= 1
            if not depth:
                return i
    raise ValueError('Estrutura do keymap incompleta.')


def _layers(source):
    clean = masked(source)
    node = re.search(r'\bkeymap\s*\{', clean)
    if not node:
        raise ValueError('Não encontrei o nó keymap.')
    start = clean.index('{', node.start())
    end = closing(clean, start)
    result = []
    cursor = start + 1
    while cursor < end:
        child = re.search(r'\b([\w-]+)\s*\{', clean[cursor:end])
        if not child:
            break
        child_start = cursor + child.start()
        brace = clean.index('{', child_start)
        child_end = closing(clean, brace)
        content = clean[brace:child_end]
        binding = re.search(r'\bbindings\s*=\s*<', content)
        if binding:
            left = brace + binding.end()
            right = clean.find('>', left, child_end)
            if right == -1:
                raise ValueError('Lista de teclas incompleta.')
            refs = list(re.finditer(r'&[A-Za-z_][\w]*', clean[left:right]))
            spans, values = [], []
            for i, ref in enumerate(refs):
                a = left + ref.start()
                b = left + refs[i+1].start() if i + 1 < len(refs) else right
                b = a + len(clean[a:b].rstrip())
                spans.append((a, b))
                values.append(' '.join(clean[a:b].split()))
            if len(values) != 38:
                raise ValueError(f'Camada {child.group(1)} tem {len(values)} teclas; esperado: 38.')
            label = re.search(r'\blabel\s*=\s*"([^"\n]+)"', source[brace:child_end])
            result.append({'name': child.group(1), 'label': label.group(1) if label else child.group(1), 'bindings': values, '_spans': spans})
        cursor = child_end + 1
    if not result:
        raise ValueError('Nenhuma camada editável encontrada.')
    return result


def parse(source):
    return [{k: v for k, v in layer.items() if not k.startswith('_')} for layer in _layers(source)]


def validate(binding):
    if not isinstance(binding, str) or len(binding) > 200:
        raise ValueError('Função de tecla inválida.')
    binding = binding.strip()
    if not re.fullmatch(r'&[A-Za-z_]\w*(?: +[A-Za-z_0-9(),]+)*', binding):
        raise ValueError('Use uma única função ZMK, por exemplo: &kp A ou &lt 1 SPACE.')
    depth = 0
    for char in binding:
        depth += (char == '(') - (char == ')')
        if depth < 0:
            raise ValueError('Parênteses inválidos.')
    if depth:
        raise ValueError('Parênteses incompletos.')
    return binding


def update(source, edits):
    layers = _layers(source)
    replacements, seen = [], set()
    if not isinstance(edits, list) or len(edits) > 2048:
        raise ValueError('Lista de alterações inválida.')
    for edit in edits:
        layer, position = edit.get('layer'), edit.get('position')
        if type(layer) is not int or type(position) is not int or not 0 <= layer < len(layers) or not 0 <= position < 38:
            raise ValueError('Camada ou posição inválida.')
        if (layer, position) in seen:
            raise ValueError('Tecla repetida na alteração.')
        seen.add((layer, position))
        binding = validate(edit.get('binding'))
        if binding != layers[layer]['bindings'][position]:
            a, b = layers[layer]['_spans'][position]
            replacements.append((a, b, binding))
    for a, b, value in sorted(replacements, reverse=True):
        source = source[:a] + value + source[b:]
    _layers(source)
    return source


def save(path, edits, expected_hash):
    path = Path(path)
    original = path.read_bytes()
    if digest(original) != expected_hash:
        raise ValueError('Arquivo alterado fora desta tela. Recarregue antes de salvar.')
    updated = update(original.decode(), edits).encode()
    if updated != original:
        backups = path.parent / 'backups'
        backups.mkdir(exist_ok=True)
        (backups / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.keymap')).write_bytes(original)
        tmp = path.with_suffix('.keymap.tmp')
        tmp.write_bytes(updated)
        os.replace(tmp, path)
    return digest(updated)


def replace(path, source, expected_hash):
    """Replace a full keymap with the same backup/CAS semantics as single-key edits."""
    path=Path(path); original=path.read_bytes()
    if digest(original)!=expected_hash: raise ValueError('Arquivo alterado. Atualize a prévia antes de aplicar.')
    if not isinstance(source,str) or len(source.encode())>200000: raise ValueError('Keymap inválido.')
    for layer in parse(source):
        for binding in layer['bindings']: validate(binding)
    updated=source.encode()
    if original!=updated:
        backups=path.parent/'backups'; backups.mkdir(exist_ok=True)
        (backups/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.keymap')).write_bytes(original)
        tmp=path.with_suffix('.keymap.tmp'); tmp.write_bytes(updated); os.replace(tmp,path)
    return digest(updated)
