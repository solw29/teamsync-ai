import React from 'react';
import {it,expect} from 'vitest';
import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {Dashboard} from './main';
import {parseReport} from './schema';
import demo from '../public/demo.json';
it('searches and filters actual report rows',()=>{
 render(<MemoryRouter><Dashboard report={parseReport(demo)}/></MemoryRouter>);
 expect(screen.getAllByRole('row')).toHaveLength(13);
 fireEvent.change(screen.getByLabelText('PR 검색'),{target:{value:'S01'}});
 expect(screen.getAllByRole('row')).toHaveLength(3);
 fireEvent.change(screen.getByLabelText('PR 검색'),{target:{value:'no-such-pr'}});
 expect(screen.getByText('검색 결과가 없습니다.')).toBeTruthy();
 cleanup();
});
it('orders by findings and handles an empty bundle',()=>{
 const first=render(<MemoryRouter><Dashboard report={parseReport(demo)}/></MemoryRouter>);
 fireEvent.change(screen.getByLabelText('정렬'),{target:{value:'reviews'}});
 expect(screen.getAllByRole('row')[1].textContent).toContain('S02-buggy');
 first.unmount();
 render(<MemoryRouter><Dashboard report={parseReport({...demo,analyses:[]})}/></MemoryRouter>);
 expect(screen.getByText('분석 결과가 없습니다. Data에서 결과 파일을 가져오세요.')).toBeTruthy();
 cleanup();
});
