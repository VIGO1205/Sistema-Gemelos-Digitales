"""Exportacion Word COM y paginas PNG para inspeccion visual."""
from pathlib import Path
import json,time
import win32com.client
import pymupdf
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'entrega/articulo_RIAI'
docx=OUT/'Articulo_RIAI_Copper_Creek.docx';pdf=docx.with_suffix('.pdf')
word=win32com.client.DispatchEx('Word.Application');word.Visible=False;word.DisplayAlerts=0
try:
    doc=word.Documents.Open(str(docx),ReadOnly=True,AddToRecentFiles=False)
    doc.Repaginate()
    doc.ExportAsFixedFormat(str(pdf),17,OpenAfterExport=False,OptimizeFor=0,BitmapMissingFonts=True,UseISO19005_1=True)
    doc.Close(False)
finally:word.Quit()
p=pymupdf.open(pdf)
pages=[]
for i,page in enumerate(p):
    page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False).save(OUT/'qa'/f'pagina_{i+1:02}.png')
    pages.append({'page':i+1,'words':len(page.get_text().split()),'text':page.get_text(),'links':len(page.get_links()),'fonts':[list(f) for f in page.get_fonts()]})
(OUT/'qa/paginas.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
print('PAGINAS',len(p));print([(x['page'],x['words']) for x in pages])
