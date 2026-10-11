"""Download the pinned Microsoft sample and extract only the required CSV."""
from pathlib import Path
import argparse, hashlib, json, urllib.request, zipfile

URL='https://github.com/microsoft/finops-toolkit/releases/download/v14/dataset-examples.zip'
ARCHIVE_SHA='d7769d9e759b5968a68affcb364235ad938a705168c546ab86cad5bbb27ff607'
SOURCE_SHA='9b192e205da384caecb627e8a4281a0229195d96a8be24bce66057b25c6a8603'

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def download(folder):
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/'EA-Cost-FOCUS_1.0.csv'
    if target.exists():
        if sha(target)!=SOURCE_SHA:raise ValueError('Existing source checksum differs; inspect it before replacing it.')
        return target
    archive=folder/'dataset-examples.zip'
    if not archive.exists():
        request=urllib.request.Request(URL,headers={'User-Agent':'Cloud-cost-portfolio/1.0'})
        with urllib.request.urlopen(request,timeout=120) as response,archive.open('wb') as dest:
            while block:=response.read(1024*1024):dest.write(block)
    if sha(archive)!=ARCHIVE_SHA:raise ValueError('Archive checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        names=[n for n in z.namelist() if Path(n).name==target.name]
        if len(names)!=1:raise ValueError('Expected exactly one matching source file')
        with z.open(names[0]) as source,target.open('wb') as dest:
            while block:=source.read(1024*1024):dest.write(block)
    if sha(target)!=SOURCE_SHA:raise ValueError('Source checksum mismatch')
    (folder/'source.json').write_text(json.dumps({'url':URL,'archive_sha256':ARCHIVE_SHA,'source_sha256':SOURCE_SHA},indent=2))
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--directory',type=Path,default=Path('.cache/source'))
    print(download(p.parse_args().directory))
