import {describe,it,expect} from 'vitest';
import sample from '../../docs/phase2/example-v2/report.json';
import legacy from '../public/demo.json';
import {parseReport} from './schema';
describe('phase2 compatibility',()=>{
 it('imports both versions without discarding evidence',()=>{
  expect(parseReport(legacy).analyses).toHaveLength(12);
  const r=parseReport(sample);expect(r.analyses).toHaveLength(1);
  expect(r.analyses[0].verification?.requirements[0].status).toBe('satisfied');
  expect(r.analyses[0].verification?.usage.inputTokens).toBeNull();
 });
 it('rejects identity mismatch',()=>{
  expect(()=>parseReport({...sample,identity:{...sample.identity,runId:99}})).toThrow();
 });
 it('rejects dangling evidence and unknown schema',()=>{
  expect(()=>parseReport({...sample,evidence:[]})).toThrow();
  expect(()=>parseReport({...sample,schemaVersion:'3.0'})).toThrow();
 });
});
