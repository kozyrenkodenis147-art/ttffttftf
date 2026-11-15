import json, os, urllib.request, zipfile

OUT = 'src/main/resources/data/minecraft/'
OLD_BOTTOM, NEW_MIN, HEIGHT = -64, -1008, 1328
BLACK = {"type": "minecraft:condition",
         "if_true": {"type": "minecraft:not", "invert": {"type": "minecraft:y_above", "anchor": {"absolute": -64},
                     "surface_depth_multiplier": 0, "add_stone_depth": False}},
         "then_run": {"type": "minecraft:block", "result_state": {"Name": "minecraft:blackstone"}}}

def get(url):
    return urllib.request.urlopen(url, timeout=180).read()

def conv(o):
    if isinstance(o, dict):
        if set(o.keys()) == {'above_bottom'}:
            return {'absolute': OLD_BOTTOM + o['above_bottom']}
        return {k: conv(v) for k, v in o.items()}
    if isinstance(o, list):
        return [conv(x) for x in o]
    return o

def write(path, data):
    p = OUT + path
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        json.dump(data, f, indent=1)

def insert_black(o):
    if isinstance(o, list):
        for i, e in enumerate(o):
            if isinstance(e, dict) and isinstance(e.get('if_true'), dict) and e['if_true'].get('random_name') == 'minecraft:deepslate':
                o.insert(i, BLACK)
                return True
        return any(insert_black(e) for e in o)
    if isinstance(o, dict):
        return any(insert_black(v) for v in o.values())
    return False

def patch(z):
    d = json.loads(z.read('data/minecraft/dimension_type/overworld.json'))
    d['min_y'], d['height'], d['logical_height'] = NEW_MIN, HEIGHT, HEIGHT
    write('dimension_type/overworld.json', d)
    ns = json.loads(z.read('data/minecraft/worldgen/noise_settings/overworld.json'))
    ns['noise']['min_y'], ns['noise']['height'] = NEW_MIN, HEIGHT
    if not insert_black(ns['surface_rule']):
        raise SystemExit('Deepslate rule not found')
    write('worldgen/noise_settings/overworld.json', ns)
    n = 0
    for name in z.namelist():
        if name.endswith('.json') and (name.startswith('data/minecraft/worldgen/placed_feature/') or name.startswith('data/minecraft/worldgen/configured_carver/')):
            raw = z.read(name).decode('utf-8')
            if 'above_bottom' in raw:
                write(name.split('data/minecraft/')[1], conv(json.loads(raw)))
                n += 1
    print('patched files with above_bottom:', n)

if __name__ == '__main__':
    man = json.loads(get('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'))
    v = next(x for x in man['versions'] if x['id'] == '1.20.1')
    meta = json.loads(get(v['url']))
    with open('/tmp/client.jar', 'wb') as f:
        f.write(get(meta['downloads']['client']['url']))
    patch(zipfile.ZipFile('/tmp/client.jar'))
    print('done')
