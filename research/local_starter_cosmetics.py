"""Native NORMAL starter clothing, separate from paid or official ownership.

Original reset 0x085a713c..0x085a7188 grants indices 0..4 for shirts,
pants and shoes. Body/face catalogs are available in the normal reset tail.
Only independently verified deployed counts enable this policy. No blanket
unlock, client availability import, custom outfit or purchase is supported.
"""
from dataclasses import dataclass
POLICY='native-normal-starter-cosmetics-v1'
COUNTS=('bodies','shirts','pants','body_suits','shoes','hats','eyes','nose','mouth')
CURRENT={'AVATAR_BODIES_CURRENT':'bodies','AVATAR_SHIRTS_CURRENT':'shirts',
         'AVATAR_PANTS_CURRENT':'pants','AVATAR_SHOES_CURRENT':'shoes',
         'AVATAR_HATS_CURRENT':'hats','AVATAR_EYES_CURRENT':'eyes',
         'AVATAR_NOSE_CURRENT':'nose','AVATAR_MOUTH_CURRENT':'mouth'}
@dataclass(frozen=True)
class CosmeticCatalog:
    policy:str
    counts:dict
    def __post_init__(self):
        if self.policy!=POLICY or type(self.counts) is not dict or set(self.counts)!=set(COUNTS):
            raise ValueError('Explicit verified native cosmetic catalog required')
        if any(type(v) is not int or not 1<=v<=768 for v in self.counts.values()):
            raise ValueError('Invalid catalog bound')
        if any(self.counts[k]<5 for k in ('shirts','pants','shoes')):
            raise ValueError('Native starter range absent from installed catalog')
        object.__setattr__(self,'counts',dict(self.counts))
    def selection(self,avatar):
        selected={}
        for field,category in CURRENT.items():
            value=avatar[field]
            limit=5 if category in ('shirts','pants','shoes') else 1 if category=='hats' else min(self.counts[category],256)
            if type(value) is not int or not 0<=value<limit:
                raise ValueError('Appearance outside verified starter policy: '+field)
            selected[field]=value
        return selected
    def project(self,avatar,selected=None):
        out=dict(avatar)
        for name in ('SHIRTS','PANTS','SHOES'):out['AVATAR_'+name+'_AVAILABLE']=31
        if selected:
            self.selection(selected)
            out.update(selected)
        return out
