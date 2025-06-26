import unittest
from unittest.mock import MagicMock, patch
from rmapy.types import RootFolder, FileMetaListBlob, FileMetaBlob, RawJsonBlob, Document, Collection

# Helper to make ThreadPoolExecutor run synchronously in tests
class SyncExecutor:
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def submit(self, fn, *args, **kwargs):
        class F:
            def result(self2): return fn(*args, **kwargs)
        return F()
    def shutdown(self, *a, **k): pass

def sync_as_completed(fs):
    return fs

class BaseReconcileTest(unittest.TestCase):
    def setUp(self):
        patcher_executor = patch('rmapy.types.ThreadPoolExecutor', new=SyncExecutor)
        patcher_as_completed = patch('concurrent.futures.as_completed', new=sync_as_completed)
        self.addCleanup(patcher_executor.stop)
        self.addCleanup(patcher_as_completed.stop)
        patcher_executor.start()
        patcher_as_completed.start()
        self.mock_client = MagicMock()
        self.mock_client.get_blob.side_effect = self.mock_get_blob
        self.mock_client.get_root_hash.side_effect = lambda: self.new_root_hash
        self.file_blobs = {}
        self.collection_blobs = {}
        self.meta_blobs = {}
        self.meta_list_blobs = {}
        self.new_root_hash = 'new_root_hash'
        self.all_filemetablobs = {}

    def make_file(self, hash, name, parent='', visibleName=None, pinned=False, size=100, createdTime='t', lastModified='t', lastOpened='t', lastOpenedPage='1'):
        if visibleName is None:
            visibleName = name
        meta_blob = RawJsonBlob(json={
            'type': 'DocumentType',
            'createdTime': createdTime,
            'lastModified': lastModified,
            'lastOpened': lastOpened,
            'lastOpenedPage': lastOpenedPage,
            'parent': parent,
            'pinned': pinned,
            'visibleName': visibleName
        }, client=self.mock_client)
        file_meta = FileMetaBlob(hash=hash, name=name, size=size, client=self.mock_client)
        file_meta._blob = MagicMock()
        file_meta._blob.metadata = meta_blob
        self.file_blobs[hash] = file_meta._blob
        self.meta_blobs[hash] = meta_blob
        self.all_filemetablobs[hash] = file_meta
        return file_meta

    def make_collection(self, hash, name, parent='', visibleName=None, version='1', pinned=False, synced=True, modified=False, deleted=False, metadataModified=False, lastModified='t', lastOpened='t', lastOpenedPage='1'):
        if visibleName is None:
            visibleName = name
        meta_blob = RawJsonBlob(json={
            'type': 'CollectionType',
            'visibleName': visibleName,
            'parent': parent,
            'lastModified': lastModified,
            'lastOpened': lastOpened,
            'lastOpenedPage': lastOpenedPage,
            'version': version,
            'pinned': pinned,
            'synced': synced,
            'modified': modified,
            'deleted': deleted,
            'metadatamodified': metadataModified
        }, client=self.mock_client)
        file_meta = FileMetaBlob(hash=hash, name=name, size=0, client=self.mock_client)
        file_meta._blob = MagicMock()
        file_meta._blob.metadata = meta_blob
        self.collection_blobs[hash] = file_meta._blob
        self.meta_blobs[hash] = meta_blob
        self.all_filemetablobs[hash] = file_meta
        return file_meta

    def mock_get_blob(self, hash_value):
        # Return the _blob for both files and folders
        for d in [self.file_blobs, self.collection_blobs]:
            if hash_value in d:
                return d[hash_value]
        if hash_value in self.meta_list_blobs:
            return self.meta_list_blobs[hash_value]
        return None

class TestBasicReconcile(BaseReconcileTest):
    def setUp(self):
        super().setUp()
        # Create two files, no folders
        self.file1_meta = self.make_file('hash1', 'doc1')
        self.file2_meta = self.make_file('hash2', 'doc2')
        self.file_list_blob = FileMetaListBlob(files=[self.file1_meta, self.file2_meta], client=self.mock_client)
        self.meta_list_blobs['old_root_hash'] = self.file_list_blob
        # For new root, create new FileMetaBlob objects for doc2 and doc3
        file2_new = self.make_file('hash2', 'doc2')
        file3_new = self.make_file('hash3', 'doc3')
        self.meta_list_blobs['new_root_hash'] = FileMetaListBlob(files=[file3_new, file2_new], client=self.mock_client)

    def test_reconcile_adds_and_removes_documents(self):
        root = RootFolder(hash='old_root_hash', list_blob=self.file_list_blob, client=self.mock_client)
        doc_names = [item.visibleName for item in root.contents if isinstance(item, Document)]
        self.assertIn('doc1', doc_names)
        self.assertIn('doc2', doc_names)
        self.assertEqual(len(doc_names), 2)
        
        ok, r = root.reconcile()
        self.assertTrue(ok)

        create_names = [item.visibleName for item in r['creates']]
        self.assertIn('doc3', create_names)
        self.assertEqual(1, len(r['creates']))

        orphan_names = [item.visibleName for item in r['orphans']]
        self.assertIn('doc1', orphan_names)
        self.assertEqual(1, len(r['orphans']))

        doc_names = [item.visibleName for item in root.contents if isinstance(item, Document)]
        self.assertNotIn('doc1', doc_names)
        self.assertIn('doc2', doc_names)
        self.assertIn('doc3', doc_names)
        self.assertEqual(len(doc_names), 2)

class TestAdvancedReconcile(BaseReconcileTest):
    def setUp(self):
        super().setUp()
        # Initial structure:
        # root
        # ├── folderA (name='folderA', hash='hashA')
        # │   ├── file1 (parent='folderA')
        # │   └── file2 (parent='folderA')
        # └── folderB (name='folderB', hash='hashB')
        #     └── file3 (parent='folderB')
        self.folderA_meta = self.make_collection('hashA', 'folderA')
        self.folderB_meta = self.make_collection('hashB', 'folderB')
        self.file1_meta = self.make_file('hash1', 'file1', parent='folderA')
        self.file2_meta = self.make_file('hash2', 'file2', parent='folderA')
        self.file3_meta = self.make_file('hash3', 'file3', parent='folderB')
        self.file_list_blob = FileMetaListBlob(
            files=[self.folderA_meta, self.folderB_meta, self.file1_meta, self.file2_meta, self.file3_meta],
            client=self.mock_client
        )
        self.meta_list_blobs['old_root_hash'] = self.file_list_blob
        # After reconcile:
        # - file2 deleted
        # - file4 added to folderB
        # - folderC added with file5
        folderA_new = self.make_collection('hashA', 'folderA')
        folderB_new = self.make_collection('hashB', 'folderB')
        folderC_new = self.make_collection('hashC', 'folderC')
        file1_new = self.make_file('hash1', 'file1', parent='folderA')
        file3_new = self.make_file('hash3', 'file3', parent='folderB')
        file4_new = self.make_file('hash4', 'file4', parent='folderB')
        file5_new = self.make_file('hash5', 'file5', parent='folderC')
        self.meta_list_blobs['new_root_hash'] = FileMetaListBlob(
            files=[folderA_new, folderB_new, folderC_new, file1_new, file3_new, file4_new, file5_new],
            client=self.mock_client
        )

    def mock_get_blob(self, hash_value):
        if hash_value == 'new_root_hash':
            return self.meta_list_blobs['new_root_hash']
        elif hash_value == 'old_root_hash':
            return self.meta_list_blobs['old_root_hash']
        return super().mock_get_blob(hash_value)

    def test_advanced_reconcile(self):
        root = RootFolder(hash='old_root_hash', list_blob=self.file_list_blob, client=self.mock_client)
        # Check initial structure
        folders = {c.visibleName: c for c in root.contents if isinstance(c, Collection)}
        self.assertIn('folderA', folders)
        self.assertIn('folderB', folders)
        self.assertNotIn('folderC', folders)
        filesA = [d.visibleName for d in folders['folderA'].contents if isinstance(d, Document)]
        filesB = [d.visibleName for d in folders['folderB'].contents if isinstance(d, Document)]
        self.assertCountEqual(filesA, ['file1', 'file2'])
        self.assertCountEqual(filesB, ['file3'])

        # Reconcile, with new root hash returned
        ok, r = root.reconcile()
        self.assertTrue(ok)

        create_names = [item.visibleName for item in r['creates']]
        self.assertIn('folderC', create_names)
        self.assertIn('file4', create_names)
        self.assertIn('file5', create_names)
        self.assertEqual(3, len(create_names))

        orphan_names = [item.visibleName for item in r['orphans']]
        self.assertIn('file2', orphan_names)
        self.assertEqual(1, len(r['orphans']))


        folders = {c.visibleName: c for c in root.contents if isinstance(c, Collection)}
        self.assertIn('folderA', folders)
        self.assertIn('folderB', folders)
        self.assertIn('folderC', folders)
        self.assertEqual(3, len(folders))
        filesA = [d.visibleName for d in folders['folderA'].contents if isinstance(d, Document)]
        filesB = [d.visibleName for d in folders['folderB'].contents if isinstance(d, Document)]
        filesC = [d.visibleName for d in folders['folderC'].contents if isinstance(d, Document)]
        self.assertIn('file1', filesA)
        self.assertNotIn('file2', filesA) # file2 deleted
        self.assertEqual(1, len(filesA))

        self.assertIn('file3', filesB)
        self.assertIn('file4', filesB) # file4 added
        self.assertEqual(2, len(filesB))
        
        self.assertIn('file5', filesC) # new folder and file
        self.assertEqual(1, len(filesC))

if __name__ == '__main__':
    unittest.main() 