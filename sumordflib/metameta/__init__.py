from typing import Optional

from rdflib import URIRef

class AnyHostURIRef(URIRef):

    hostreg: Optional[dict[str, str]]

    def __new__(cls, value, hostreg=None):
        cls.hostreg = hostreg or {'file': 'https://localhost:8999'}
        return super().__new__(cls, value)

    def replace_host(self):
        self.replace('file://', self.hostreg['file'])




def any_host_uri_ref(value, hostreg=None):
    if value.startswith('file://'):
        value = value.replace('file://', hostreg['file'])
    return AnyHostURIRef(value, hostreg)



def test_any_host_uri_ref():
    x = AnyHostURIRef('file:///Volumes/ExternalData/admin/Developer/Projects/my-assistant/content-vacuum/')
    assert hasattr(x, 'hostreg')
    assert isinstance(x, URIRef)
    assert isinstance(x, str)
    assert x.hostreg['file'] == 'https://localhost:8999'


