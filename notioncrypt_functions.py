from urllib.parse import urlparse
from uuid import UUID

from cryptography.fernet import InvalidToken

UNSUPPORTED_BLOCKTYPES = ["unsupported", "child_page"]


def get_url(object_id):
    """Return the URL for the object with the given id."""
    return "https://notion.so/" + UUID(object_id).hex

def get_id(url):
    """Return the id of the object behind the given URL."""

    parsed = urlparse(url)
    if "notion.so" != parsed.netloc[-9:]:
        raise ValueError("Not a valid Notion URL.")
    
    # remove args from link
    path = parsed.path
    if "?" in path:
        pos = path.index("?")
        path = path[:pos]

    if len(path) < 32:
        raise ValueError("The path in the URL seems to be incorrect.")
    raw_id = path[-32:]
    
    return str(UUID(raw_id))

def get_meta_details(client, pageid):
    """
        Get the relevant meta information about page,
        only allow pages whose parents are also pages. Pages that belong
        to a notion database or toplevel workspace will not be processed

        returns:
        Either a dictionary containing relevant meta details of a page
        or None if the page isnt a child of a page
    """
    PAGE_IDENTIFER = "page_id"
    page = client.pages.retrieve(pageid)
    if page["parent"]["type"] == PAGE_IDENTIFER:
        parentid = page["parent"]["page_id"]
        titles = [title["text"]["content"] for title in page["properties"]["title"]["title"]]
        relevantinfo = {
                            "parent": {"page_id": parentid},
                            "properties": {
                                "title": [{"text": {
                                            "content": title
                                                }
                                            } for title in titles]
                            }
                        }
        return relevantinfo
    return None 


def create_new_page(client, meta_pagedetails, children_contentblocks):
    """
        Create a new page with its page contents and attach it 
        to the parent passed
    """
    if children_contentblocks:
        page_payload = dict(meta_pagedetails)
        
        if page_payload and children_contentblocks:
            page_payload["children"] = children_contentblocks
            client.pages.create(**page_payload)

def get_children_blocks(client, blockid):
    """
        Recursively get all the contents of a block (a page is also a block).
        all the content are also blocks that might have content of thier own
        hence the recursion.
    """
    # get the inital set of objects (limit of 100 blocks)
    partiallist = client.blocks.children.list(blockid)
    has_more = partiallist.pop("has_more", False)
    next_cursor = partiallist.pop("next_cursor", "")
    children = partiallist.pop("results", [])

    # get the remaining blocks if they exist
    while has_more:
        partiallist = client.blocks.children.list(blockid, start_cursor=next_cursor)
        has_more = partiallist.pop("has_more", False)
        next_cursor = partiallist.pop("next_cursor", "")
        otherchildren = partiallist.pop("results", [])

        children += otherchildren
        
    # recursively get every single sub block
    for block in children:
        if block["has_children"]:
            blocktype = block["type"]
            block[blocktype]["children"] = get_children_blocks(client, block["id"])
    return children

def append_children_to_parentblock(client, blockid, children):
    """ append children to a block"""
    client.blocks.children.append(blockid, **{"children":children})

def encryptcontent(blocks, fernetobject):
    """
        recursively encrypts all the text content of text blocks

        returns a list of encrypted blocks

        Exceptions:
            raises an UnsupportedBlockError if any of the blocks passed arent textlike
    """
    blocks = list(blocks)
    for block in blocks:
        blocktype = block["type"]
        if blocktype in UNSUPPORTED_BLOCKTYPES:
            raise UnsupportedBlockError
        else:
            for richtextobjects in block[blocktype]["text"]:
                if richtextobjects["type"] == "text":
                    plaincontent = richtextobjects["text"]["content"]
                    encryptedcontent = fernetobject.encrypt(plaincontent.encode("utf-8"))
                    richtextobjects["text"]["content"] = encryptedcontent.decode()

                # remove the plain text attribute as it is a duplicate of content but isnt encrypted
                richtextobjects.pop("plain_text", "")
            if block["has_children"]:
                block[blocktype]["children"] = encryptcontent(block[blocktype]["children"], 
                                                        fernetobject
                                                    )
        block[blocktype]["text"]
    return blocks

def decryptcontent(blocks, fernetobject):
    """
        recursively decrypts all the text content of textlike blocks

        returns a list of decrypted blocks

        Exceptions:
            raises an UnsupportedBlockError if any of the blocks passed arent textlike
            raises an Invalid Token Error if the blocks passed cannot be decrypted
    """
    for block in blocks:
        blocktype = block["type"]
        if blocktype in UNSUPPORTED_BLOCKTYPES:
            raise UnsupportedBlockError
        for richtextobjects in block[blocktype]["text"]:
            if richtextobjects["type"] == "text":
                encryptedcontent = richtextobjects["text"]["content"]
                try:
                    plaincontent = fernetobject.decrypt(encryptedcontent.encode("utf-8"))
                except InvalidToken:
                    raise
                richtextobjects["text"]["content"] = plaincontent.decode()
        
        if block["has_children"]:
            block[blocktype]["children"] = decryptcontent(block[blocktype]["children"],
                                                    fernetobject
                                                )
    return blocks


# Custom Exception
class UnsupportedBlockError(Exception):
    """ error for when an unsupported block is encountered"""

    def __init__(self, msg="Only Textlike Blocks are currently allowed"):
        self.message = msg
        super().__init__(self.message)

