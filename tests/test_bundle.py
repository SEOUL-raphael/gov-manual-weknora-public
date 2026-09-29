# 배포 구성 검증
import hashlib,json,tempfile,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_bundle import verify
class BundleTests(unittest.TestCase):
    def test_valid_and_modified_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); p=root/'file.txt';p.write_bytes(b'expected')
            (root/'BUNDLE-MANIFEST.json').write_text(json.dumps({'files':[{'path':'file.txt','bytes':8,'sha256':hashlib.sha256(b'expected').hexdigest()}]}))
            verify(root);p.write_bytes(b'changed!')
            with self.assertRaises(ValueError): verify(root)
    def test_path_escape_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'BUNDLE-MANIFEST.json').write_text(json.dumps({'files':[{'path':'../outside','bytes':0,'sha256':''}]}))
            with self.assertRaises(ValueError): verify(root)
if __name__=='__main__': unittest.main()
