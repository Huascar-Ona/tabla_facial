import psycopg2
from datetime import date
import isoweek
import sys

def get_sequence(cr, emp, fecha_max):
    fecha_max_year = fecha_max.year
    fecha_max_week = fecha_max.isocalendar()[1]
    sequence_set = []
    week = None
    year = None    
    cr.execute("select anio,semana,secuencia from asistmil_asignaciones where emp=%s and (anio<=%s or (anio=%s and semana<=%s)) order by anio desc,semana desc", (emp,fecha_max_year,fecha_max_year,fecha_max_week))
    for row in cr.fetchall():
        row_year = row[0]
        row_week = row[1]
        row_seq = row[2]
        if week is not None:
            prev_week = week - 1
            prev_year = year - 1
            #Condiciones para terminar el conjunto
            #1. La semana no es consecutiva
            if row_week != prev_week:
                #Checar posible consecutivo cross-year
                if row_year == prev_year:
                    last_week_of_prev_year = isoweek.Week.last_week_of_year(prev_year).week
                    if row_week != last_week_of_prev_year:
                        break
                else:
                    break
            #2. Secuencia repetida
            if row_seq in [x[2] for x in sequence_set]:
                break
        sequence_set.append(row)
        year = row_year
        week = row_week
    sequence_set.reverse()
    return sequence_set

def extrapolate(cr, emp, fecha_ex, fecha_seq):
    ex_year, ex_week, ex_day = fecha_ex.isocalendar()
    sequence = get_sequence(cr, emp, fecha_seq)
    if not sequence:
        return -1
    year_start = sequence[0][0]
    week_start = sequence[0][1]
    year = year_start
    week = week_start
    seq_idx = 0
    if (year == ex_year and week > ex_week) or year > ex_year:
        return -1
    while True:
        seq = sequence[seq_idx][2]
        if year == ex_year and week == ex_week:
            break
        week += 1
        if week > isoweek.Week.last_week_of_year(year).week:
            week = 1
            year += 1
        seq_idx += 1
        if seq_idx == len(sequence):
            seq_idx = 0
    return seq

if __name__ == '__main__':
    conn = psycopg2.connect("dbname=offset11sept user=openerp password=zentella host=localhost")
    cr = conn.cursor()
    emp = sys.argv[1]
    cr.execute("select anio,semana,secuencia from asistmil_asignaciones where emp=%s order by anio desc,semana desc", (emp,))
    for row in cr.fetchall():
        print row
    print "-----"
    sequence = get_sequence(cr, emp, date.today())
    for row in sequence:
        print row
    seq = extrapolate(cr, emp, date(2017,12,15), date.today())
    print seq
    conn.close()

