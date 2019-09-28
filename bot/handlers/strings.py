__START_MESSAGE = ("Ciao! 👋\n\nBenvenuto su <b>GrandaBus Unofficial Bot</b>, "
                   "il bot <b>NON UFFICIALE</b> che ti permette di conoscere gli "
                   "orari del trasporto pubblico del consorzio GrandaBus.\n\n"
                   "/disclaimer\n\n"
                   "<i>Ultimo aggiornamento dati: {date}.</i>\n\n")


def start_message(date):
    if date:
        d = f'{date.day}/{date.month}/{date.year} {date.hour}:{date.minute}'
    else:
        d = 'mai'

    return __START_MESSAGE.format(date=d)


def disclaimer_message():
    return ("GrandaBus Unofficial Bot non è associato in alcun modo con il "
            "consorzio [GrandaBus](http://grandabus.it/).\n\n"
            "[Codice sorgente del bot](...)\n\n"
            "/menu per tornare al menu")


def short_line_descr(code, name, timetable_url):
    return (f'👉 <b>{code}</b>\n'
            f'<b>Nome linea: </b>{name}\n'
            f'<b>Orari: </b>{timetable_url}\n\n')


def no_line_found_by_city_message():
    return ("Nessuna linea trovata. Prova con un'altra città")


def no_line_found_by_code_message():
    return ("Nessuna linea trovata. Prova con un altro codice")


def no_line_found_by_location():
    return ('Nessuna linea trovata nelle tue vicinanze')


def get_go_to_menu_message():
    return "Tocca /menu per tornare al menu"
