import {describe,it,expect} from 'vitest';
import demo from '../public/demo.json';
import {parseReport,codeUrl} from './schema';
describe('import contract',()=>{
 it('accepts real sanitized reports',()=>expect(parseReport(demo).analyses).toHaveLength(12));
 it('rejects unsupported versions and missing fields',()=>{expect(()=>parseReport({...demo,schemaVersion:'2'})).toThrow();expect(()=>parseReport({schemaVersion:'1.0'})).toThrow()});
 it('rejects dangerous links and duplicates',()=>{const data=structuredClone(demo);data.analyses[0].githubUrl='javascript:alert(1)' as never;expect(()=>parseReport(data)).toThrow();expect(()=>parseReport({...demo,analyses:[demo.analyses[0],demo.analyses[0]]})).toThrow()});
 it('does not create links from anonymized data',()=>expect(codeUrl(parseReport(demo).analyses[0],'file.py',1)).toBeNull());
});
