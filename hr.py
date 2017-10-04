# -*- coding: utf-8 -*-
from openerp.osv import osv,fields
from datetime import datetime
from extrapolar_secuencia import extrapolate

class diasvac(osv.Model):
    _name = "hr.diasvac"

    _columns = {
        'anio_anti': fields.integer(u"Años antigüedad"),
        'dias': fields.integer(u"Días"),
        'dias1': fields.integer(u"Días1")
    }

class cale_asue(osv.Model):
    _name = "hr.caleasue"
    
    _columns = {
        'fe_asueto': fields.date("Fecha asueto"),
        'tipo': fields.selection([('O','Oficial'),('V','Vacaciones')], string="Tipo"),
        'coment': fields.text("Comentario")
    }
    
class hr_employee(osv.Model):
    _inherit = "hr.employee"
    
    def _get_diasvac(self, cr, uid, ids, fields, args, context=None):
        res = {}
        if context is None:
            context = {}
        
        #Cargar en memoria la tabla de diasvac para un acceso más rápido
        diasvac = {}
        cr.execute("select anio_anti,dias,dias1 from hr_diasvac")
        for row in cr.fetchall():
            diasvac[row[0]] = (row[1],row[2])
            
        for rec in self.browse(cr, uid, ids):
            fecha_alta = datetime.strptime(rec.fecha_alta, "%Y-%m-%d")
            #Tomar como fecha del periodo solicitado la fecha actual, a menos que en el context venga otra explícitamente
            if not 'fecha_fin' in context:
                fecha_fin = datetime.now()
            else:
                fecha_fin = datetime.strptime(context.get("fecha_fin"), "%Y-%m-%d")
            
            #Calcular antiguedad
            antiguedad = int((fecha_fin - fecha_alta).days / 365.25)
            
            #Si tiene 1 o más años de antiguedad
            if antiguedad >= 1:
                if antiguedad not in diasvac:
                    raise osv.except_osv("Error al calcular vacaciones", u"No hay una entrada en la tabla de días de vacaciones para %s años de antigüedad"%antiguedad)
                #Revisar si es Administrativo o Produccion (administrativo=quincenal, produccion=semanal)
                if not rec.category_ids or rec.category_ids[0].name.lower() == 'quincenal':
                    if fecha_alta >= datetime(2015, 3, 1):
                        dias = diasvac[antiguedad][1]
                    else:
                        dias = diasvac[antiguedad][0]
                else:
                    dias = diasvac[antiguedad][0]
                
            #Si tiene menos de un año
            else:
                antiguedad_meses = int((fecha_fin - fecha_alta).days / 30.4375)
                if not rec.category_ids or rec.category_ids[0].name.lower() == 'quincenal':
                    dias = int(antiguedad_meses * 0.5)
                else:
                    dias = int(antiguedad_meses * 0.75)
                    
            #Contamos las vacaciones del año actual según la tabla CaleAsue
            #Para cada fecha si aplica como vacaciones se suma a las vacaciones gozadas (tdacu)
            #Si la fecha del asueto está en el futuro, se suma a las vacaciones por gozar (diacue)
            cr.execute("select fe_asueto from hr_caleasue where tipo='V' and extract(year from fe_asueto) = %s", (fecha_fin.year,))
            diacue = 0
            tdacu = 0
            condicion_sabado = [1,5,7,8,9,12,13,16,471,472]
            tipo_vacaciones = ('0002','0018','0030','0031','0028')
            for row in cr.fetchall():
                fe_asueto = datetime.strptime(row[0], "%Y-%m-%d")
                secuencia_asueto = extrapolate(cr, rec.cod_emp, fe_asueto, fecha_fin)
                es_sabado = fe_asueto.isoweekday() == 6
                #Si la fecha de asueto está dentro del periodo
                if fecha_alta <= fe_asueto <= fecha_fin:
                    #Si no es sábado o cumple con las restricciones de sábado
                    if not es_sabado or secuencia_asueto in condicion_sabado:
                        #Buscar registro de incidencia que corresponda a la fecha y ver que efectivamente no haya tenido actividades
                        cr.execute("select id from asistmil_inciden where empleado=%s and fecha=%s and tipo in " + repr(tipo_vacaciones), (rec.cod_emp, fe_asueto,))
                        if not cr.fetchall():
                            tdacu += 1
                #Si esta en el futuro
                elif fe_asueto > fecha_fin:
                    #Si no es sábado o cumple con las restricciones de sábado aumentar la variable de vacaciones por gozar
                    if not es_sabado or secuencia_asueto in condicion_sabado:
                        diacue += 1
                        
            #Contar cuántos registros tiene el empleado de tipo 0001 (Vacaciones) y 0035 (Vacaciones pierde premio) en lo que va del año
            inicio_anio = datetime(fecha_fin.year, 1, 1)
            cr.execute("""select count(*) from asistmil_inciden
                          where tipo in ('0001','0035')
                          and empleado=%s
                          and fecha between %s and %s""", (rec.cod_emp, inicio_anio, fecha_fin))
            a001 = cr.fetchone()[0]
                          
            #Finalmente se calculan las vacaciones restantes por medio de la siguiente formula:
            #Vacaciones restantes x gozar = (Total dias - Días a cuenta de vacaciones - Días Pedidos  - Resto Asignados)
            vacrest = dias - tdacu - a001 - diacue 
            
            res[rec.id] = {
                'vac_tot': dias,
                'vac_g': tdacu + a001,
                'vac_xg': diacue,
                'vac_rest': vacrest
            }
                
        return res

    _columns = {
        'vac_tot': fields.function(_get_diasvac, method=True, type="integer", string=u"Total Días Vac", multi="vac"),
        'vac_g': fields.function(_get_diasvac, method=True, type="integer", string=u"Vac Gozadas", multi="vac"),
        'vac_xg': fields.function(_get_diasvac, method=True, type="integer", string=u"Vac por gozar RH", multi="vac"),
        'vac_rest': fields.function(_get_diasvac, method=True, type="integer", string=u"Vac por pedir", multi="vac"),
    }
