"""Figuras originales del estudio, derivadas de CSV y del artefacto de escena."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import LogNorm

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'entrega/articulo_RIAI'; T=OUT/'tablas'; F=OUT/'figuras'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.labelsize':8,'axes.titlesize':8,'legend.fontsize':7,'xtick.labelsize':7,'ytick.labelsize':7,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
W=8.5/2.54
def export(fig,name):
    fig.savefig(F/(name+'.png'),dpi=300,bbox_inches=None,facecolor='white')
    fig.savefig(F/(name+'.pdf'),bbox_inches=None,facecolor='white')
    plt.close(fig)

def fig01():
    fig,ax=plt.subplots(figsize=(W,2.6)); ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
    labels=['CSV públicos de Copper Creek\nCollares · trayectorias · ensayos','Control estructural y composites\nCoordenadas X, Y, Z → Cu medido','Evaluación por sondajes y por zonas\nCinco modelos y dos referencias','Artefacto publicado y soporte\nFastAPI · consulta de coordenadas','Visualización 3D y revisión\nCentros de cubos · métricas · reportes']
    ys=np.linspace(.90,.10,5)
    for j,(label,y) in enumerate(zip(labels,ys)):
        ax.add_patch(FancyBboxPatch((.045,y-.068),.91,.136,boxstyle='round,pad=0.012',lw=.8,facecolor='#f1f3f4' if j!=3 else '#e1edf3',edgecolor='#333333'))
        ax.text(.5,y,label,ha='center',va='center',fontsize=8)
        if j<4: ax.annotate('',xy=(.5,y-.128),xytext=(.5,y-.080),arrowprops={'arrowstyle':'->','lw':.9,'color':'#333333'})
    fig.subplots_adjust(left=.02,right=.98,bottom=.02,top=.98);export(fig,'fig01_flujo')

def fig02():
    s=pd.read_csv(T/'composites.csv')
    fig,(ax,bx)=plt.subplots(2,1,figsize=(W,3.65),gridspec_kw={'height_ratios':[1.4,1]})
    x=s.x-548000;y=s.y-3623400
    c=ax.scatter(x,y,c=s.cu_pct,norm=LogNorm(.003,9),s=3,cmap='cividis',rasterized=True)
    ax.set_xlabel('Este − 548 000 (m)');ax.set_ylabel('Norte − 3 623 400 (m)');ax.set_aspect('equal');ax.set_title('(a) Composites georreferenciados',loc='left')
    cb=fig.colorbar(c,ax=ax,pad=.025);cb.set_label('Cobre medido (% Cu)')
    bx.hist(s.cu_pct,bins=np.linspace(0,9,37),color='#5d6c7b',edgecolor='white',linewidth=.35)
    bx.set_yscale('log');bx.set_ylabel('Frecuencia (escala log)');bx.set_xlabel('Cobre medido (% Cu)');bx.set_title('(b) Distribución de leyes',loc='left')
    fig.tight_layout(pad=.7);export(fig,'fig02_muestras')

def fig03():
    df=pd.read_csv(T/'metricas_pliegues.csv');df=df[(df.protocol=='sondajes')&(df.seed==42)]
    fig,ax=plt.subplots(figsize=(W,2.5))
    specs=[('Ordinary Kriging','OK','D','-','#756bb1'),('Random Forest','RF','o','-','#006b8b'),('XGBoost','XGBoost','^','-.','#ab5a16'),('Stacking Ensemble','Stacking','v','--','#40814b'),('NN + Bayesian Kriging','NN+OK','P','-','#a02c59'),('IDW3','IDW3 (ref.)','s','--','#333333'),('Media','Media (ref.)','x',':','#777777')]
    for name,label,marker,ls,color in specs:
        g=df[df.model==name];ax.plot(g.fold,g.rmse,label=label,marker=marker,ls=ls,color=color,ms=4,lw=1)
    ax.set_xticks(range(1,6));ax.set_xlabel('Grupo de validación');ax.set_ylabel('RMSE (puntos porcentuales de Cu)');ax.legend(frameon=False,ncol=3,loc='lower center',bbox_to_anchor=(.5,1.01),fontsize=6.5,columnspacing=.7);ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.18)
    fig.tight_layout(pad=.7);export(fig,'fig03_error_grupos')

def fig04():
    winner=json.loads((OUT/'evidencia/seleccion_cinco.json').read_text(encoding='utf-8'))['study_winner']
    oo=pd.read_csv(T/'predicciones_fuera_muestra.csv');g=oo[(oo.protocol=='sondajes')&(oo.model==winner)&oo.supported]
    fig,(ax,bx)=plt.subplots(2,1,figsize=(W,3.5))
    limit=max(9,float(np.ceil(max(g.actual.max(),g.predicted.max()))))
    ax.scatter(g.actual,g.predicted,s=6,alpha=.28,color='#244e62',rasterized=True);ax.plot([0,limit],[0,limit],'k--',lw=.8)
    ax.set_xlim(0,limit);ax.set_ylim(min(0,float(g.predicted.min())*1.1),limit);ax.set_xlabel('Cobre medido (% Cu)');ax.set_ylabel('Cobre predicho (% Cu)');ax.set_title('(a) Predicciones fuera de muestra',loc='left')
    dist_rows=[]
    for low,high in [(0,20),(20,40),(40,60),(60,80),(80,120.001)]:
        v=g[(g.nearest_train_m>=low)&(g.nearest_train_m<high)]
        dist_rows.append({'low_m':low,'high_m':min(high,120),'n':len(v),'mae':np.abs(v.actual-v.predicted).mean(),'rmse':np.mean((v.actual-v.predicted)**2)**.5})
    dd=pd.DataFrame(dist_rows);dd.to_csv(T/'error_distancia.csv',index=False)
    bx.bar(np.arange(5),dd.mae,color='#708896',edgecolor='#253b46',lw=.6)
    for i,r in dd.iterrows(): bx.text(i,r.mae+.012,str(int(r.n)),ha='center',fontsize=7)
    bx.set_xticks(range(5),['0–20','20–40','40–60','60–80','80–120']);bx.set_xlabel('Distancia al composite de entrenamiento más cercano (m)',fontsize=6.7);bx.set_ylabel('MAE (puntos porcentuales de Cu)');bx.set_title('(b) Error por distancia; etiquetas = muestras',loc='left')
    bx.set_ylim(0,dd.mae.max()*1.24)
    fig.tight_layout(pad=.7,h_pad=1.1);export(fig,'fig04_predicciones')

def fig05():
    scene=json.loads((ROOT/'backend/data/copper_creek_mammoth.json').read_text(encoding='utf-8'));blocks=pd.DataFrame(scene['blocks'])
    blocks[['id','x','y','z','bench','cu_bayesian','cu_idw3','support_holes','nearest_drillhole_m']].rename(columns={'cu_bayesian':'cu_rf_pct','cu_idw3':'cu_idw3_pct'}).to_csv(T/'centros_cubos.csv',index=False)
    fig=plt.figure(figsize=(W,2.6));ax=fig.add_subplot(111,projection='3d')
    p=ax.scatter(blocks.x-548470,blocks.y-3623920,blocks.z,s=2,c=blocks.cu_bayesian,cmap='cividis',vmin=0,vmax=1,rasterized=True)
    ax.set_xlabel('Este relativo (m)',labelpad=-1,fontsize=7);ax.set_ylabel('Norte relativo (m)',labelpad=-1,fontsize=7);ax.set_zlabel('');ax.tick_params(pad=0,labelsize=6);ax.view_init(elev=25,azim=-60);ax.set_box_aspect((1,1,.65))
    ax.text2D(.60,.95,'Elevación (m)',transform=ax.transAxes,fontsize=7)
    ax.set_position([0,.05,.75,.90]);cax=fig.add_axes([.84,.25,.035,.48])
    cb=fig.colorbar(p,cax=cax,extend='max');cb.set_label('Predicción puntual (% Cu)',fontsize=7);cb.ax.tick_params(labelsize=6)
    export(fig,'fig05_centros_cubos')

if __name__=='__main__':
    for func in [fig01,fig02,fig03,fig04,fig05]: func()
    print('Cinco figuras PNG 300 dpi y PDF vectorial generadas.')
