import{S}from"./state.js";import{$,table}from"./common.js";export function render(){table("dataTable",S.rows.slice(0,500));$("metrics").textContent=`${S.rows.length.toLocaleString()} displayed rows`}
