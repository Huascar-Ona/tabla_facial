# -*- coding: utf-8 -*-
from openerp.osv import osv,fields

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
