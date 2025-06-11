# rmapy
This is an (unofficial) Remarkable Cloud API Client written in Python, forked from [subutux/rmapy](https://github.com/subutux/rmapy) to add support for new "sync/v3" endpoints.

Still a work-in-progress, with only read-only support currently. But I haven't found another library in 2025 which still works with the Remarkable API -- if you have, please share!


## Walkthrough

```bash
$ python3
>>> from rmapy.api import Client
>>> from rmapy.types import *
>>> api: Client = Client()

>>> # This get_root_folder step will take a while while the file structure graph nodes are built.
>>> root: RootFolder = api.get_root_folder()

>>> # After that, the entire directory tree is traversable locally.
>>> for item in root.contents:
...     print(f'* {type(item)}: {item.visibleName}')
...     if item.type == 'CollectionType':
...         for subitem in item.contents:
...             print(f'  * {type(subitem)}: {subitem.visibleName}')

* <class 'rmapy.types.Collection'>: 2023
  * <class 'rmapy.types.Document'>: Tax Return
  * <class 'rmapy.types.Collection'>: Italy Trip
* <class 'rmapy.types.Collection'>: Pocket
  * <class 'rmapy.types.Document'>: We have used too many levels of abstractions and now the future looks bleak
  * <class 'rmapy.types.Document'>: Connecting Bash to Nix
  * <class 'rmapy.types.Document'>: Production Twitter on One Machine? 100Gbps NICs and NVMe are fast
* <class 'rmapy.types.Collection'>: Substack
  * <class 'rmapy.types.Document'>: The Pragmatic Engineer - The Pulse 60: Tech IPOs are back! [136563243]
  * <class 'rmapy.types.Document'>: Ken Klippenstein - Congress Wants Intel to Go After Online "Harassment," Blimps to Surveil Canadian Border [145622193]
* <class 'rmapy.types.Collection'>: Newspapers
  * <class 'rmapy.types.Document'>: Washington Post 20240910
  * <class 'rmapy.types.Document'>: New York Times 20240912
  * <class 'rmapy.types.Document'>: New York Times 20240908
* <class 'rmapy.types.Document'>: Quick sheets
* <class 'rmapy.types.Document'>: Reading group
[...]

>>> # The RootFolder contains Collection's...
>>> str(root.contents[0])[:600]
"Collection(uuid='03b50d1c-17f2-4dcf-a94d-c2ce9087294c', hash='bb48afd605b0a692d010966a309d3e1ac2f4314facb72ebca666ccdb5edc95dc', contents=[Document(uuid='39713454-3265-4cd0-a51b-c09605728c59', hash='25aa2192eab1ea46d162d6e9597360f24ca2108383728c5a6271b8aad758b507', createdTime='0', lastModified='1717880444891', lastOpened='1712886248140', lastOpenedPage=25, parentUuid='03b50d1c-17f2-4dcf-a94d-c2ce9087294c', pinned=False, type='DocumentType', visibleName='Tax Return'), Document(uuid='82e7a5bf-cb5a-42f1-8124-3af113c48eb0', hash='d0d91f7ff...',"

>>> root.contents[0].meta_blob
RawJsonBlob(json={'createdTime': '1717880415503', 'lastModified': '1717880415502', 'parent': '', 'pinned': False, 'type': 'CollectionType', 'visibleName': '2023'}, type='RawJsonBlob')

>>> root.contents[0].uuid
'03b50d1c-17f2-4dcf-a94d-c2ce9087294c'

>>> # And Document's.
>>> root.contents[0].contents[0]
Document(uuid='39713454-3265-4cd0-a51b-c09605728c59', hash='25aa2192eab1ea46d162d6e9597360f24ca2108383728c5a6271b8aad758b507', createdTime='0', lastModified='1717880444891', lastOpened='1712886248140', lastOpenedPage=25, parentUuid='03b50d1c-17f2-4dcf-a94d-c2ce9087294c', pinned=False, type='DocumentType', visibleName='Tax Return')

>>> # Each Document is itself represented by multiple types of blobs.
>>> for file in root.contents[0].contents[0].meta_list_blob.files:
...     print(f'{type(file)} {file}')
<class 'rmapy.types.FileMetaBlob'> FileMetaBlob(hash='67b7e969f05c86013285c634b1343457819b0b132f93826e18fa92f93e7d562d', name='39713454-3265-4cd0-a51b-c09605728c59.content', size='3127', type='FileMetaBlob')
<class 'rmapy.types.FileMetaBlob'> FileMetaBlob(hash='e9f050e63b9f57f2f322143c5725f0c33bcf7751fda163f54adb2209926d8910', name='39713454-3265-4cd0-a51b-c09605728c59.metadata', size='376', type='FileMetaBlob')
<class 'rmapy.types.FileMetaBlob'> FileMetaBlob(hash='01027b30b742bce395cbd307c51bf2d6a16d1da3630daacf5b2a3b365cded876', name='39713454-3265-4cd0-a51b-c09605728c59.pagedata', size='162', type='FileMetaBlob')
<class 'rmapy.types.FileMetaBlob'> FileMetaBlob(hash='54f9c8967e771bfeb3fa4671e54b5321688942d64f2b4547b97cf76da5ba2f98', name='39713454-3265-4cd0-a51b-c09605728c59.pdf', size='1571729', type='FileMetaBlob')
<class 'rmapy.types.FileMetaBlob'> FileMetaBlob(hash='ea84e975380d14fb87ec313015c0af7e6f3f89cf5cfe68bb41292eb1855c8c91', name='39713454-3265-4cd0-a51b-c09605728c59/2724d184-8c16-4118-811e-5f1856d8516f.rm', size='12893', type='FileMetaBlob')
<class 'rmapy.types.FileMetaBlob'> FileMetaBlob(hash='7141310099283a908908736e21e3c18ea9f3cbb4046ddde22e8fd25a59297cf2', name='39713454-3265-4cd0-a51b-c09605728c59/40181924-0754-4181-80a0-f8aaa8baa8f6.rm', size='8462', type='FileMetaBlob')
<class 'rmapy.types.FileMetaBlob'> FileMetaBlob(hash='ee3bca38085390f50bad13641c1420ad8f2fc3c1e2ec89129427e9d71fe75c74', name='39713454-3265-4cd0-a51b-c09605728c59/b5371b40-d6cd-4069-9bc3-996ebf626043.rm', size='14234', type='FileMetaBlob')
<class 'rmapy.types.FileMetaBlob'> FileMetaBlob(hash='8b83012f089abef71067508bf48c5af08acbe3096dfa72836277818206526038', name='39713454-3265-4cd0-a51b-c09605728c59/e1d1e7f9-06a8-4454-84a8-02d5397e475d.rm', size='8837', type='FileMetaBlob')

>>> # However, you need to query for the contents of each meta blob to get its real contents.
>>> for file in root.contents[0].contents[0].meta_list_blob.files:
...     print(f'{type(file)=} {type(file.get_blob())=}')
type(file)=<class 'rmapy.types.FileMetaBlob'> type(file.get_blob())=<class 'rmapy.types.RawJsonBlob'>
type(file)=<class 'rmapy.types.FileMetaBlob'> type(file.get_blob())=<class 'rmapy.types.RawJsonBlob'>
type(file)=<class 'rmapy.types.FileMetaBlob'> type(file.get_blob())=<class 'rmapy.types.RawFileBlob'>
type(file)=<class 'rmapy.types.FileMetaBlob'> type(file.get_blob())=<class 'rmapy.types.RawFileBlob'>
type(file)=<class 'rmapy.types.FileMetaBlob'> type(file.get_blob())=<class 'rmapy.types.RawFileBlob'>
type(file)=<class 'rmapy.types.FileMetaBlob'> type(file.get_blob())=<class 'rmapy.types.RawFileBlob'>
type(file)=<class 'rmapy.types.FileMetaBlob'> type(file.get_blob())=<class 'rmapy.types.RawFileBlob'>
type(file)=<class 'rmapy.types.FileMetaBlob'> type(file.get_blob())=<class 'rmapy.types.RawFileBlob'>

# To get the raw contents of the pdf backing this document:
>>> root.contents[0].contents[0].meta_list_blob.files[3]
FileMetaBlob(hash='54f9c8967e771bfeb3fa4671e54b5321688942d64f2b4547b97cf76da5ba2f98', name='39713454-3265-4cd0-a51b-c09605728c59.pdf', size='1571729', type='FileMetaBlob')

# ...call get_blob() on the pdf file within the document.
# Note that this is the first outbound network call since the initial get_root_folder().
>>> str(root.contents[0].contents[0].meta_list_blob.files[3].get_blob())[:100]
"RawFileBlob(contentType='application/pdf', content=b'%PDF-1.6\\r%\\xe2\\xe3\\xcf\\xd3\\r\\n366 0 obj\\r<</Li"

>>> with open("/tmp/file.pdf", "wb") as f:
...     f.write(root.contents[0].contents[0].meta_list_blob.files[3].get_blob().content)

>>> # Note that calling get_blob() on an object is just a wrapper around calling `api.get_blob(hash)`:
>>> str(api.get_blob('54f9c8967e771bfeb3fa4671e54b5321688942d64f2b4547b97cf76da5ba2f98'))[:100]
"RawFileBlob(contentType='application/pdf', content=b'%PDF-1.6\\r%\\xe2\\xe3\\xcf\\xd3\\r\\n366 0 obj\\r<</Li"
```