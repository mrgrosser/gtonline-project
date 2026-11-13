"""Create private-server keys locally; export only public drill material."""
import json,os,secrets
from pathlib import Path
from Crypto.PublicKey import RSA,DSA
from Crypto.Hash import SHA1
from Crypto.Signature import DSS
root=Path(__file__).parent
snapshot=json.loads((root/'evidence/public-trust-20261113.json').read_text());f=snapshot['public_fields']
def integer(name):return int.from_bytes(bytes.fromhex(f[name]),'big')
os.umask(0o077);directory=root/'private-server-keys';directory.mkdir(mode=0o700)
rsa=RSA.generate(2048);p,q,g=[integer('server_dsa_'+x) for x in ('p','q','g')]
x=secrets.randbelow(q-1)+1;dsa=DSA.construct((pow(g,x,p),g,p,q,x))
(directory/'rsa.pem').write_bytes(rsa.export_key());(directory/'dsa.pem').write_bytes(dsa.export_key())
new=dict(f);new.update(server_rsa_n=int(rsa.n).to_bytes(256,'big').hex(),server_rsa_e=int(rsa.e).to_bytes(4,'little').hex(),server_dsa_y=int(dsa.y).to_bytes(96,'big').hex())
digest=SHA1.new(b'Golden Tee temporary public trust drill 20261113')
snapshot.update(new_public_fields=new,test_digest=digest.hexdigest(),test_signature=DSS.new(dsa,'deterministic-rfc6979').sign(digest).hex(),executable_sha256='3d407b648d16da0d0e6c324420c10a51eb432f3068fa0bbc1f1561c92d250d1d')
(root/'evidence/trust-drill-config.json').write_text(json.dumps(snapshot))
print('Fresh private-server keys saved locally; public-only drill configuration prepared')
