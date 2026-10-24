import {describe,it,expect} from 'vitest';
import {importStatus,canConfirm,decodeFile,statusLabel,formatImportDate,fieldLabel} from './import-model';

describe('trade import outcomes',()=>{
 it('does not describe validated rows as booked',()=>{
  expect(importStatus({status:'NEEDS_CORRECTION',total:10,valid:9,invalid:1,applied:0,replayed:0})).toContain('0 booked');
  expect(canConfirm({status:'NEEDS_CORRECTION',total:10,valid:9,invalid:1,applied:0,replayed:0})).toBe(false);
 });
 it('offers confirmation only for a fully valid reviewed batch',()=>{
  expect(canConfirm({status:'READY',total:2,valid:2,invalid:0,applied:0,replayed:0})).toBe(true);
  expect(importStatus({status:'APPLIED',total:2,valid:2,invalid:0,applied:0,replayed:2})).toContain('2 already booked');
 });
 it('extracts a file payload without changing its bytes',()=>{
  expect(decodeFile('data:application/octet-stream;base64,AAEC')).toBe('AAEC');
  expect(()=>decodeFile('not a data URL')).toThrow();
 });
 it('distinguishes validation readiness from actual booking in badges',()=>{
  expect(statusLabel('READY')).toBe('Ready to book');
  expect(statusLabel('RECEIVED')).toBe('Awaiting validation');
  expect(statusLabel('APPLIED')).toBe('Booking completed');
  expect(statusLabel('INVALID')).toBe('Needs correction');
  expect(statusLabel('REPLAY')).toBe('Already booked');
 });
 it('formats dates in an explicit consistent timezone and tolerates missing history timestamps',()=>{
  expect(formatImportDate('2026-10-19T10:00:00+00:00')).toBe('19 Oct 2026, 10:00 UTC');
  expect(formatImportDate('invalid')).toBe('Date unavailable');
 });
 it('uses readable field names without replacing the stable source key',()=>{
  expect(fieldLabel('executionPrice')).toBe('Execution price');
  expect(fieldLabel('valuationEffectiveDate')).toBe('Effective valuation date');
  expect(fieldLabel('property:immutable-id')).toBe('Custom field');
  expect(fieldLabel('unknownField')).toBe('unknownField');
 });
});
