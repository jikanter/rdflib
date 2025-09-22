"""
A simplified port of some of the useful bits in cwm.
Does not include the built-in sparql parser.

The goal here is to not depend on cwm and all of it's dependencies at all.
"""
import traceback
import sys
from sumordflib import resource as uripath
from sumordflib.metameta.why import newTopLevelFormula
import urllib.request
import os

HTTP_Content_Type = 'content-type'
print_all_file_names = False

class UnsupportedLanguageError(Exception):
    pass

class SecurityError(IOError):
    pass

class OfflineAccessError:
    pass

class DocumentAccessError(IOError):
    def __init__(self, uri, info):
        self._uri = uri
        self._info = info


# A little code to represent a value that can be set
# and read; a singleton. In essence, this is a little
# prettier than a one element list
def setting(self, val=None):
    if val is not None:
        self[0] = val
    return self[0]

sandBoxed = setting.__get__([False])


def cacheHack(addr):
    """ If on a plane, hack remote w3.org access to local access
    """
    real = "http://www.w3.org/"
    local = "/devel/WWW/"
    suffixes = ["", ".rdf", ".n3"]
    if addr.startswith(real):
        rest = local + addr[len(real):]
        for s in suffixes:
            fn = rest + s
            try:
                os.stat(fn)
                progress("Offline: Using local copy %s" % fn)
                return "file://" + fn
            except OSError:
                continue
    return addr


class Diagnostics:

    def __init__(self, chatty_flag=0):
        self.chatty_flag = chatty_flag

diag = Diagnostics()

"""
TODO: replace this with tqdm
"""
def progress(*args: object) -> object:
    level = len(traceback.extract_stack())
    sys.stderr.write(" "*level)
    for a in args:
        i = 0
        a = str(a)
        while 1:
##    lineCount[0] += 1
            i = a.find("\n", i)
            if i < 0: break
            a = a[:i+1] + (" "*level) + a[i+1:]
            i = i+1
        q = u"%s " % (a,)[0]
        sys.stderr.write(q)
##        if lineCount[0] > 20:
##            lineCount[0] = 0
##            sys.stdin.readline()
    sys.stderr.write("\n")

def webget(addr, referer=None, types=None):
    """Open a URI for reading; return a file-like object with .headers
    cf http://www.w3.org/TR/2004/REC-webarch-20041215/#dereference-uri
    """
    if not types: types = []
    if diag.chatty_flag > 7: progress("Accessing: " + addr)
    if sandBoxed():
        if addr[:5] == 'file:':
            raise SecurityError('local file access prohibited')

#    addr = cacheHack(addr)

    # work around python stdlib bugs with data: URIs
    # buggy in 2.4.2 with CStringIO
    if addr[:5] == 'data:':
        # return open_data(addr)
        return urllib.request.urlopen(addr)

    req = urllib.request.Request(addr)

    if types:
        req.add_header('Accept', ','.join(types))

    if referer: #consistently misspelt
        req.add_header('Referer', referer)

    stream =  urllib.request.urlopen(req)

    if print_all_file_names:
        diag.file_list.append(addr)

    return stream

def urlopenForRDF(addr, referer=None):
    """Access the web, with a preference for RDF
    """
    return webget(addr,
                  types=['text/rdf+n3',
                         'application/rdf+xml'
       #                  ,'application/x-turtle'    # Why not ask for turtle?
                         ],
                  referer = referer)



def load(store, uri=None, openFormula=None, asIfFrom=None, contentType=None,
         flags="", referer=None, why=None, topLevel=False):
    """Get and parse document.  Guesses format if necessary.

    uri:      if None, load from standard input.
    remember: if 1, store as metadata the relationship between this URI and this formula.

    Returns:  top-level formula of the parsed document.
    Raises:   IOError, SyntaxError, DocumentError

    This is an independent function, as it is fairly independent
    of the store. However, it is natural to call it as a method on the store.
    And a proliferation of APIs confuses.
    """
    #    if referer is None:
    #        raise RuntimeError("We are trying to force things to include a referer header")
    try:
        baseURI = uripath.base()
        if uri != None:
            addr = uripath.join(baseURI, uri)  # Make abs from relative
            if diag.chatty_flag > 40: progress("Taking input from " + addr)
            netStream = urlopenForRDF(addr, referer)
            if diag.chatty_flag > 60:
                progress("   Headers for %s: %s\n" % (addr, netStream.headers.items()))
            receivedContentType = netStream.headers.get(HTTP_Content_Type, None)
        else:
            if diag.chatty_flag > 40: progress("Taking input from standard input")
            addr = uripath.join(baseURI, "STDIN")  # Make abs from relative
            netStream = sys.stdin
            receivedContentType = None

        #    if diag.chatty_flag > 19: progress("HTTP Headers:" +`netStream.headers`)
        #    @@How to get at all headers??
        #    @@ Get sensible net errors and produce dignostics

        guess = None
        if receivedContentType:
            if diag.chatty_flag > 9:
                progress("Recieved Content-type: " + repr(
                    receivedContentType) + " for " + addr)
            if receivedContentType.find('xml') >= 0 or (
                receivedContentType.find('rdf') >= 0
                and not (receivedContentType.find('n3') >= 0)):
                guess = "application/rdf+xml"
            elif receivedContentType.find('n3') >= 0:
                guess = "text/rdf+n3"
        if guess == None and contentType:
            if diag.chatty_flag > 9:
                progress("Given Content-type: " + repr(contentType) + " for " + addr)
            if contentType.find('xml') >= 0 or (
                contentType.find('rdf') >= 0 and not (contentType.find('n3') >= 0)):
                guess = "application/rdf+xml"
            elif contentType.find('n3') >= 0:
                guess = "text/rdf+n3"
            elif contentType.find('sparql') >= 0 or contentType.find('rq'):
                guess = "x-application/sparql"
        buffer = netStream.read()
        if guess == None:

            # can't be XML if it starts with these...
            if buffer[0:1] == "#" or buffer[0:7] == "@prefix":
                guess = 'text/rdf+n3'
            elif buffer[0:6] == 'PREFIX' or buffer[0:4] == 'BASE':
                guess = "x-application/sparql"
            elif buffer.find('xmlns="') >= 0 or buffer.find('xmlns:') >= 0:  # "
                guess = 'application/rdf+xml'
            else:
                guess = 'text/rdf+n3'
            if diag.chatty_flag > 9: progress("Guessed ContentType:" + guess)
    except (IOError, OSError):
        raise DocumentAccessError(addr, sys.exc_info())

    if asIfFrom == None:
        asIfFrom = addr
    if openFormula != None:
        F = openFormula
    else:
        F = store.newFormula()
    if topLevel:
        newTopLevelFormula(F)
    import os
    if guess == "x-application/sparql":
        raise UnsupportedLanguageError("This module does not support SPARQL, you will either need to use rdflib, legacy cwm, or a dedicated parser")
    elif guess == 'application/rdf+xml':
        if diag.chatty_flag > 49: progress("Parsing as RDF")
        #       import sax2rdf, xml.sax._exceptions
        #       p = sax2rdf.RDFXMLParser(store, F,  thisDoc=asIfFrom, flags=flags)
        if flags == 'rdflib' or int(os.environ.get("CWM_RDFLIB", 0)):
            parser = 'rdflib'
            flags = ''
        else:
            parser = os.environ.get("CWM_RDF_PARSER", "sax2rdf")
        import rdfxml
        p = rdfxml.rdfxmlparser(store, F, thisDoc=asIfFrom, flags=flags,
                                parser=parser, why=why)

        p.feed(buffer)
        F = p.close()
    else:
        assert guess == 'text/rdf+n3'
        if diag.chatty_flag > 49: progress("Parsing as N3")
        if os.environ.get("CWM_N3_PARSER", 0) == 'n3p':
            from . import n3p_tm
            from . import triple_maker
            tm = triple_maker.TripleMaker(formula=F, store=store)
            p = n3p_tm.n3p_tm(asIfFrom, tm)
        else:
            from Minestrone.DataModel.Notation3 import notation3
            p = notation3.SinkParser(store, F, thisDoc=asIfFrom, flags=flags, why=why)
        try:
            p.startDoc()
            p.feed(buffer)
            p.endDoc()
        except:
            progress("Failed to parse %s" % uri or buffer)
            raise

    if not openFormula:
        F = F.close()
    return F
