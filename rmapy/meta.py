class Meta(object):
    """ Meta represents a real object expected in most
    calls by the remarkable API

    This class is used to be subclassed by for new types.

    Attributes:
        id: ID of the meta object.
        hash: Hash of the file contents.
        type: Currently there are only 2 known types: DocumentType &
            CollectionType.
        visibleName: The human name of the object.
        lastModified: Last modified date (epoch timestamp as a string).
        lastOpened: Last opened date (epoch timestamp as a string).
        parent: ID of the object which is this object's parent. If empty,
            this object is is the root folder. This can be an ID of a
            CollectionType.
        pinned: If the object is pinned to this folder.
        fileType: The file extension of the object, e.g. 'pdf', 'epub', 'notebook'
    """

    id = ""
    hash = ""
    type = ""
    visibleName = ""
    lastModified = ""
    lastOpened = ""
    parent = ""
    pinned = False
    fileType = ""

    def __init__(self, **kwargs):
        k_keys = self.to_dict().keys()
        for k in k_keys:
            setattr(self, k, kwargs.get(k, getattr(self, k)))

    def to_dict(self) -> dict:
        """Return a dict representation of this object.

        Used for API Calls.

        Returns
            a dict of the current object.
        """

        return {
            "id": self.id,
            "hash": self.hash,
            "parent": self.parent,
            "fileType": self.fileType,
            "pinned": self.pinned,
            "type": self.type,
            "visibleName": self.visibleName,
            "lastOpened": self.lastOpened,
            "lastModified": self.lastModified
        }

