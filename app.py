from flask import Flask,render_template,request,redirect,url_for,flash,Response
import json
from database import init_db,connect
import tournament as t
app=Flask(__name__); app.secret_key='cambia-esta-clave'
init_db()

@app.route('/')
def home():
    ts=t.teams(); ms=t.matches(); table=t.standings()
    with connect() as db: generated=db.execute("SELECT value FROM settings WHERE key='calendar'").fetchone()['value']=='1'
    return render_template('index.html',teams=ts,matches=ms,table=table,generated=generated,done=t.league_done(),champion=t.champion())

@app.post('/teams')
def save_teams():
    try: t.register([request.form.get(f't{i}','') for i in range(1,11)]); flash('Equipos registrados.','ok')
    except ValueError as e: flash(str(e),'err')
    return redirect(url_for('home')+'#equipos')

@app.post('/calendar')
def calendar():
    try: t.generate(); flash('Calendario completo generado.','ok')
    except ValueError as e: flash(str(e),'err')
    return redirect(url_for('home')+'#calendario')

@app.post('/result/<int:mid>')
def result(mid):
    try: t.save_result(mid,int(request.form['hg']),int(request.form['ag'])); flash('Marcador guardado.','ok')
    except (ValueError,KeyError) as e: flash(str(e) or 'Marcador inválido.','err')
    return redirect(url_for('home')+'#jornadas')

@app.post('/semis')
def semis():
    try: t.create_semis(); flash('Semifinales creadas.','ok')
    except ValueError as e: flash(str(e),'err')
    return redirect(url_for('home')+'#semifinales')

@app.post('/penalties/<int:mid>')
def penalties(mid):
    try: t.save_penalties(mid,int(request.form['hp']),int(request.form['ap'])); flash('Penaltis guardados.','ok')
    except (ValueError,KeyError) as e: flash(str(e) or 'Tanda inválida.','err')
    return redirect(url_for('home')+'#semifinales')

@app.post('/final')
def final():
    try: t.create_final(); flash('Final creada.','ok')
    except ValueError as e: flash(str(e),'err')
    return redirect(url_for('home')+'#final')

@app.post('/reset')
def reset(): t.reset(); flash('Torneo reiniciado.','ok'); return redirect(url_for('home'))

@app.get('/export')
def export():
    data={'equipos':[dict(x) for x in t.teams()],'partidos':[dict(x) for x in t.matches()],'tabla':t.standings()}
    return Response(json.dumps(data,ensure_ascii=False,indent=2),mimetype='application/json',headers={'Content-Disposition':'attachment; filename=uncsm_respaldo.json'})

if __name__=='__main__': app.run(debug=True)
