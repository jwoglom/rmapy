from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import Union, Optional, Dict, TypedDict, List, Tuple
from .document import Document
from logging import getLogger
import logging
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

log = getLogger("rmapy")
log.setLevel(logging.INFO)

MetaBlob = Dict[str, str]

THREADS = 25

@dataclass_json
@dataclass
class FileMetaBlob:
    client: 'Client' = field(default=None, repr=False, kw_only=True) # type: ignore

    hash: str
    name: str
    size: int
    type: str = 'FileMetaBlob'

    _blob: 'AbstractBlob' = field(default=None, repr=False)

    def get_blob(self) -> 'AbstractBlob':
        if not self._blob:
            self._blob = self.client.get_blob(self.hash)
        return self._blob

@dataclass_json
@dataclass
class FileMetaListBlob:
    client: 'Client' = field(default=None, repr=False, kw_only=True) # type: ignore

    files: List[FileMetaBlob]
    type: str = 'FileMetaListBlob'

    _metadata: 'RawJsonBlob' = field(default=None, repr=False)

    @property
    def metadata(self) -> Optional['RawJsonBlob']:
        if not self._metadata:
            for f in self.files:
                if f.name.endswith('.metadata'):
                    self._metadata = f.get_blob()
        return self._metadata

@dataclass_json

@dataclass
class RawFileBlob:
    client: 'Client' = field(default=None, repr=False, kw_only=True) # type: ignore

    contentType: str
    content: bytes
    type: str = 'RawFileBlob'

@dataclass_json

@dataclass
class RawJsonBlob:
    client: 'Client' = field(default=None, repr=False, kw_only=True) # type: ignore

    json: Union[Dict, List]
    type: str = 'RawJsonBlob'

@dataclass_json
@dataclass
class Document:
    client: 'Client' = field(default=None, repr=False, kw_only=True) # type: ignore

    uuid: str
    hash: str
    meta_blob: RawJsonBlob = field(repr=False)
    meta_list_blob: FileMetaListBlob = field(repr=False)

    createdTime: str = field(init=False)
    lastModified: str = field(init=False)
    lastOpened: str = field(init=False)
    lastOpenedPage: str = field(init=False)
    parentUuid: str = field(init=False)
    pinned: bool = field(init=False)
    type: str = field(init=False)
    visibleName: str = field(init=False)

    def __post_init__(self):
        self.createdTime = self.meta_blob.json.get('createdTime')
        self.lastModified = self.meta_blob.json.get('lastModified')
        self.lastOpened = self.meta_blob.json.get('lastOpened')
        self.lastOpenedPage = self.meta_blob.json.get('lastOpenedPage')
        self.parentUuid = self.meta_blob.json.get('parent')
        self.pinned = self.meta_blob.json.get('pinned')
        self.type = self.meta_blob.json.get('type')
        self.visibleName = self.meta_blob.json.get('visibleName')
    
    def __eq__(self, other: 'Document'):
        return self.hash == other.hash and self.uuid == other.uuid

@dataclass_json
@dataclass
class Collection:
    client: 'Client' = field(default=None, repr=False, kw_only=True) # type: ignore

    meta_blob: RawJsonBlob = field(repr=False)
    uuid: str
    hash: str
    contents: List['DocumentOrCollection'] = field(default_factory=list)

    visibleName: str = field(init=False)
    type: str = field(init=False)
    parentUuid: str = field(init=False)
    lastModified: str = field(init=False)
    lastOpened: str = field(init=False)
    lastOpenedPage: str = field(init=False)
    version: str = field(init=False)
    pinned: bool = field(init=False)
    synced: bool = field(init=False)
    modified: bool = field(init=False)
    deleted: bool = field(init=False)
    metadataModified: bool = field(init=False)

    def __post_init__(self):
        self.visibleName = self.meta_blob.json.get('visibleName')
        self.type = self.meta_blob.json.get('type')
        self.parentUuid = self.meta_blob.json.get('parent')
        self.lastModified = self.meta_blob.json.get('lastModified')
        self.lastOpened = self.meta_blob.json.get('lastOpened')
        self.lastOpenedPage = self.meta_blob.json.get('lastOpenedPage')
        self.version = self.meta_blob.json.get('version')
        self.pinned = self.meta_blob.json.get('pinned')
        self.synced = self.meta_blob.json.get('synced')
        self.modified = self.meta_blob.json.get('modified')
        self.deleted = self.meta_blob.json.get('deleted')
        self.metadataModified = self.meta_blob.json.get('metadatamodified')
    
    def __eq__(self, other: 'Collection'):
        return self.hash == other.hash and self.uuid == other.uuid

@dataclass_json
@dataclass
class RootFolder:
    client: 'Client' = field(default=None, repr=False, kw_only=True) # type: ignore

    hash: str
    list_blob: FileMetaListBlob = field(repr=False)

    contents: List['DocumentOrCollection'] = field(default_factory=list)

    def _process_file_meta(self, file_meta: FileMetaBlob) -> Optional[Tuple[str, Union[Document, Collection]]]:
        """Process a single file metadata and return the appropriate object if valid."""
        file_blob = file_meta.get_blob()
        if not file_blob:
            return None
            
        file_metadata = file_blob.metadata
        if not file_metadata or not file_metadata.json:
            return None
            
        if file_metadata.json.get('type') == 'DocumentType':
            return file_meta.name, Document(uuid=file_meta.name, hash=file_meta.hash, meta_blob=file_metadata, meta_list_blob=file_blob)
        elif file_metadata.json.get('type') == 'CollectionType':
            return file_meta.name, Collection(uuid=file_meta.name, hash=file_meta.hash, meta_blob=file_metadata)
        return None

    def _organize_contents(self, documents: List[Document], collections: Dict[str, Collection]) -> None:
        """Organize documents and collections into their proper hierarchy."""

        # Add a fake collection for "trash" which is referenced by some children for deleted but recoverable items
        if 'trash' not in collections.keys():
            collections['trash'] = Collection(uuid='trash', hash='', meta_blob=RawJsonBlob(json={}), client=None)


        # Place files inside folders
        for document in documents:
            if document.parentUuid:
                if document.parentUuid not in collections:
                    log.warning(f"Orphaned file: {document=} parent uuid does not exist")
                    continue
                collections[document.parentUuid].contents.append(document)
        
        # Place folders inside folders
        for collection in collections.values():
            if collection.parentUuid:
                if collection.parentUuid not in collections:
                    log.warning(f"Orphaned collection: {collection=} parent uuid does not exist")
                    continue
                collections[collection.parentUuid].contents.append(collection)
        
        # Hide the trash
        del collections['trash']

        root_collections = list(filter(lambda c: not c.parentUuid, collections.values()))
        root_files = list(filter(lambda f: not f.parentUuid, documents))
        self.contents = root_collections + root_files

    def __post_init__(self):
        documents = []
        collections = {}
        log.info(f"Root folder traversing {len(self.list_blob.files)} files")
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            future_to_file = {executor.submit(self._process_file_meta, file_meta): file_meta 
                            for file_meta in self.list_blob.files}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_file)):
                if i % 20 == 0:
                    log.info(f"Root folder traversal {int(i / len(self.list_blob.files) * 100)}% complete...")
                
                result = future.result()
                if result:
                    name, item = result
                    if isinstance(item, Document):
                        documents.append(item)
                    else:
                        collections[name] = item

        self._organize_contents(documents, collections)

    def reconcile(self):
        new_hash = self.client.get_root_hash()
        if hash == new_hash:
            return
        new_list_blob = self.client.get_blob(new_hash)
        all_hashes = set()
        documents = []
        collections = {}
        
        def _traverse_tree(nodes: List[DocumentOrCollection]):
            for node in nodes:
                all_hashes.add(node.hash)
                if isinstance(node, Collection):
                    _traverse_tree(node.contents)
                    collections[node.uuid] = node
                else:
                    documents.append(node)
        _traverse_tree(self.contents)
        
        new_hashes = set()
        creates = []
        
        for file_meta in new_list_blob.files:
            new_hashes.add(file_meta.hash)
        
        # Process new files in parallel
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            future_to_file = {executor.submit(self._process_file_meta, file_meta): file_meta 
                            for file_meta in new_list_blob.files 
                            if file_meta.hash not in all_hashes}
            
            for future in concurrent.futures.as_completed(future_to_file):
                result = future.result()
                if result:
                    name, item = result
                    creates.append(item)
                    if isinstance(item, Document):
                        documents.append(item)
                    else:
                        collections[name] = item

        self._organize_contents(documents, collections)

        orphans = []
        def _remove_orphans(parent: Optional[DocumentOrCollection], nodes: List[DocumentOrCollection]):
            for node in nodes:
                if isinstance(node, Collection):
                    _remove_orphans(node, node.contents)
                if node.hash not in new_hashes:
                    log.info(f"Orphaned {node=}")
                    orphans.append(node)
                    if parent:
                        parent.contents.remove(node)
                    else:
                        self.contents.remove(node)

        _remove_orphans(None, self.contents)
        log.info(f"Reconcile complete: {creates=}, {orphans=}")







            

AbstractBlob = Union[FileMetaBlob, FileMetaListBlob, RawFileBlob, RawJsonBlob]
DocumentOrCollection = Union[Document, Collection]