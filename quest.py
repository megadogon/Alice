from flask import request
import logging
import json
from user import DbUser, findUser, createUser, commit
from response import Response
from images import Image
import maps


# начало обработки запроса от Алисы
def main():
    # выводим запрос в лог
    logging.info('Request: %r', request.json)
    # создаем начальный ответ
    response = Response(request)
    # обрабатываем запрос
    handle_dialog(response, request.json)
    # выводим ответ в лог
    logging.info('Response: %r', response.res)
    return json.dumps(response.res)


# обрабатываем запрос
def handle_dialog(res, req):
    # текст команды, которую ввел пользователь
    command = req['request']['original_utterance'].lower()

    # обработчик пинга
    if command == 'ping':
        res.addText('pong')
        return

    # получаем ID пользователя
    user_id = req['session']['user_id']

    # если пользователь новый, то просим представиться
    if req['session']['new']:
        res.addText('Привет! Назови свое имя!')
        # создаем класс для хранения информации о пользователе
        user = createUser(user_id)
        # сохраняем пользователя в базе данных
        commit()
        return

    # находим пользователя
    user = findUser(user_id)

    # если пользователь еще не представился
    if user.name is None:
        first_name = get_first_name(req)

        if first_name is None:
            res.addText('Не расслышала имя. Повтори, пожалуйста!')
            return

        user.name = first_name
        res.addText('Приятно познакомиться, ' + first_name.title() + '.')
        res.addText('Давай поиграем.')
        command = None

    # обработчик 1 комнаты
    if user.room == 1:
        Room1(res, req, user, command)

    # обработчик 2 комнаты
    elif user.room == 2:
        Room2(res, req, user, command)

    # обработчик 3 комнаты
    elif user.room == 3:
        Room3(res, req, user, command)

    # обработчик 4 комнаты
    elif user.room == 4:
        Room4(res, req, user, command)

    # обработчик Москвы
    else:
        Moscow(res, req, user, command)

    # сохраняем пользователя в базе данных
    commit()


# обработчик 1 комнаты
def Room1(res, req, user, command):
    user.room = 1

    if command == 'покажи комнату':
        if not user.seif:
            res.setImage('Комната с закрытым сейфом', Image.ROOM1_SEIF_CLOSED)
        elif not user.key3:
            res.setImage('Комната с открытым сейфом с ключём внутри', Image.ROOM1_SEIF_OPENED_KEY)
        else:
            res.setImage('Комната с пустым открытым сейфом', Image.ROOM1_SEIF_OPENED)


    elif command == 'открыть сейф':
        if user.seif:
            res.addText('Сейф уже открыт.')
        else:
            res.addText('Сейф закрыт, нужен пароль.')

    elif command == 'открыть сейф паролем 1234':
        if user.seif:
            res.addText('Сейф уже открыт.')
        else:
            res.addText('Долго подбирая код вы воспользовались надписью на стене и открыли сейф.')
            res.addText('В сейфе лежит ключ.')
            user.seif = True

    elif command == 'взять ключ' and user.seif:
        if user.key3:
            res.addText('Вы уже взяли ключ.')
        else:
            res.addText('Вы взяли ключ.')
            user.key3 = True

    elif command == 'выйти из комнаты':
        Room2(res, req, user, None)
        return

    else:
        if command:
            res.addText('Непонятная команда.')
        res.addText('Вы в какой-то комнате.')
        res.addText('Вам нужно выбраться отсюда.')
        res.addText('В комнате есть дверь, в углу сейф.')

    res.addText('Выберите команду:')

    res.addButton('покажи комнату')
    if not user.seif:
        res.addButton('открыть сейф')
    if user.password and not user.seif:
        res.addButton('открыть сейф паролем 1234')
    if not user.key3 and user.seif:
        res.addButton('взять ключ')
    res.addButton('выйти из комнаты')


# обработчик 2 комнаты
def Room2(res, req, user: DbUser, command):
    user.password = True
    user.room = 2

    if command == 'покажи комнату':
        if not user.window:
            res.setImage('Комната с окном', Image.ROOM2)
        else:
            res.setImage('Комната с окном, а под ним табуретка', Image.ROOM2_TABURETKA)

    elif command == 'зайти в начальную комнату':
        Room1(res, req, user, None)
        return

    elif command == 'открыть дверь справа ключом':
        if user.opened3:
            res.addText('Дверь уже открыта.')
        elif user.key3:
            res.addText('Вы открыли дверь.')
            user.opened3 = True
        else:
            res.addText('У вас нет ключа.')

    elif command == 'открыть дверь спереди ключом':
        if user.opened4:
            res.addText('Дверь уже открыта.')
        elif user.key4:
            res.addText('Вы открыли дверь.')
            user.opened4 = True
        elif user.key3:
            res.addText('Ключ не подходит.')
        else:
            res.addText('У вас нет ключа.')

    elif command == 'зайти в комнату справа':
        if user.opened3:
            Room3(res, req, user, None)
            return
        else:
            res.addText('Дверь справа закрыта на ключ.')

    elif command == 'зайти в комнату спереди':
        if user.opened4:
            Room4(res, req, user, None)
            return
        else:
            res.addText('Дверь спереди закрыта на ключ.')


    elif command == 'вылезти в окно':
        if user.window:
            Moscow(res, req, user, None)
            return
        else:
            res.addText('Окно слишком высоко.')

    elif command == 'поставить табуретку под окно':
        if user.window:
            res.addText('Табуретка уже стоит под окном.')
        elif user.taburetka:
            res.addText('Вы поставили табуретку под окно.')
            user.window = True
            user.taburetka = False
        else:
            res.addText('У вас нет табуретки.')

    else:
        if command:
            res.addText('Непонятная команда.')
        res.addText('Вы во второй комнате.')
        res.addText('Здесь 3 двери, одна в начальную комнату, вторая в комнату справа, третья в комнату спереди.')
        res.addText('Высоко под потолком окно.')
        res.addText('На стене надпись 1234, но вы бы ни за что не догадались, что это код от сейфа.')

    res.addText('Выберите команду:')

    res.addButton('покажи комнату')
    res.addButton('зайти в начальную комнату')
    res.addButton('зайти в комнату справа')
    res.addButton('зайти в комнату спереди')
    res.addButton('вылезти в окно')
    if user.taburetka and not user.window:
        res.addButton('поставить табуретку под окно')
    if (user.key3 or user.key4) and not user.opened3:
        res.addButton('открыть дверь справа ключом')
    if (user.key3 or user.key4) and not user.opened4:
        res.addButton('открыть дверь спереди ключом')


# обработчик 3 комнаты
def Room3(res, req, user, command):
    user.room = 3

    if command == 'покажи комнату':
        if not user.taburetka:
            if not user.key4:
                res.setImage('Комната с табуреткой, на ней ключ', Image.ROOM3_TABURETKA)
            else:
                res.setImage('Комната с табуреткой', Image.ROOM3_TABURETKA)
        else:
            res.setImage('Пустая комната', Image.ROOM3)

    elif command == 'выйти из комнаты':
        Room2(res, req, user, None)
        return

    elif command == 'взять ключ':
        if not user.key4:
            res.addText('Вы взяли ключ.')
            user.key4 = True
        else:
            res.addText('Вы уже взяли ключ.')

    elif command == 'поднять табуретку' and user.key4:
        if user.taburetka:
            res.addText('Она у вас в руках.')
        elif not user.choko:
            res.addText('Табуретка оказалась слишком тяжелая, у вас не хватило сил ее поднять.')
        else:
            res.addText('Вы с великим и упорным трудом подняли табуретку.')
            user.taburetka = True

    elif command == 'поставить табуретку':
        if user.taburetka:
            res.addText('Вы поставили табуретку обратно.')
            user.taburetka = False
        else:
            res.addText('Не путайте кнопки!')

    else:
        if command:
            res.addText('Непонятная команда.')
        res.addText('Вы в третьей комнате.')
        if not user.taburetka:
            res.addText('Здесь табуретка и дверь.')
            if not user.key4:
                res.addText('На табуретке лежит еще один ключ!')
        else:
            res.addText('Интересно стоять в пустой комнате с табуреткой в руках.')

    res.addText('Выберите команду:')

    res.addButton('покажи комнату')
    res.addButton('выйти из комнаты')
    if not user.key4:
        res.addButton('взять ключ')
    elif user.taburetka:
        res.addButton('поставить табуретку')
    else:
        res.addButton('поднять табуретку')


# обработчик 4 комнаты
def Room4(res, req, user: DbUser, command):
    user.room = 4

    if command == 'покажи комнату':
        if user.fridge:
            res.setImage('Комната с открытым холодильником', Image.ROOM4_OPENED)
        else:
            res.setImage('Комната с закрытым холодильником', Image.ROOM4_CLOSED)

    elif command == 'выйти из комнаты':
        Room2(res, req, user, None)
        return

    elif command == 'открыть холодильник':
        res.addText('Вы открыли холодильник.')
        if not user.choko:
            res.addText('Внутри лежит шоколадка.')
        else:
            res.addText('Внутри пусто.')
        user.fridge = True

    elif command == 'закрыть холодильник':
        res.addText('Вы закрыли холодильник.')
        user.fridge = False

    elif command == 'съесть шокаладку':
        if user.choko:
            res.addText('Вы ее уже съели!')
        else:
            res.addText('Вы съели шоколадку и ощутили огромный прилив сил.')
        user.choko = True

    else:
        if command:
            res.addText('Непонятная команда.')
        res.addText('Вы в четверной комнате.')
        if user.fridge:
            if user.choko:
                res.addText('Здесь стоит пустой открытый холодильник.')
            else:
                res.addText('Здесь стоит открытый холодильник с шоколадкой внутри.')
        else:
            res.addText('Здесь стоит закрытый холодильник.')

    res.addText('Выберите команду:')

    res.addButton('покажи комнату')
    res.addButton('выйти из комнаты')
    if user.fridge:
        res.addButton('закрыть холодильник')
    else:
        res.addButton('открыть холодильник')

    if user.fridge and not user.choko:
        res.addButton('съесть шокаладку')


# состояние - пользователь отгадывает город
GUESS_CITY = 1
# состояние - пользователь выбирает место, где праздновать победу
CHOOSE_PLACE = 2
# состояние - пользоватль выбирает подходит место или нет
CHOOSE_YES_NO = 3


# обработчик Москвы
def Moscow(res, req, user, command):
    user.room = None

    if user.state == CHOOSE_YES_NO:
        if command == 'да':
            res.addText('Отлично! Квест пройден!')
            res.endSession()

        elif command == 'нет':
            res.addText('А где именно вы хотите отметить?')
            user.state = CHOOSE_PLACE

        elif command == 'покажи на карте' or command == 'как дойти?':
            res.addText('Подходит?')
            res.addButton('да')
            res.addButton('нет')

        else:
            res.addText('Не понятно. Так да или нет?')
            res.addButton('да')
            res.addButton('нет')

    elif user.state == CHOOSE_PLACE:
        # получение информации об огранизации
        organization = maps.getOrganization(command)

        # если организация найдена
        if organization:
            # название организации
            name = organization['properties']['CompanyMetaData']['name']
            # ID организации
            id = organization['properties']['CompanyMetaData']['id']
            # координаты организации
            coords = organization['geometry']['coordinates']

            res.addText('Рекомендую ' + command + ' - ' + name + '.')
            res.addText('Подходит?')
            res.addButton('да')
            res.addButton('нет')

            # построение ссылки для отображения карточки организации
            # описание, как получить ссылку на карточку организации:
            # https://tech.yandex.ru/yandex-apps-launch/maps/doc/concepts/yandexmaps-web-docpage/#yandexmaps-web__org

            res.addLink('покажи на карте', f'https://yandex.ru/maps/org/{id}')

            # построение ссылки для отображения маршрута
            # описание как получить ссылку для построение марштура:
            # https://tech.yandex.ru/yandex-apps-launch/maps/doc/concepts/yandexmaps-web-docpage/#yandexmaps-web__buildroute

            coord1 = f"{coords[1]},{coords[0]}"
            coord2 = f"{maps.OUR_COORD[1]},{maps.OUR_COORD[0]}"
            res.addLink('как дойти?', f'https://yandex.ru/maps/?rtext={coord1}~{coord2}&rtt=pd')
            user.state = CHOOSE_YES_NO

        else:
            res.addText('Не знаю такого места.')
            res.addText('Попробуйте другой вариант.')
            res.addButton('кафе')
            res.addButton('пиццерия')
            res.addButton('кинотеатр')

    elif user.state == GUESS_CITY:
        if command == 'покажи город':
            res.setImage('Город под названием ******. Отгадывай!', Image.MOSCOW)
            res.addText('Отгадывай')
        else:
            # поиск города в запросе пользователя
            city = get_city(req)
            if city == 'москва':
                res.addText('Вы отгадали.')
                res.addText('Прямо перед вами Московский исторический музей.')
                res.addText('После стольких усилий вы наверняка хотите отпразновать победу.')
                res.addText('Выберите место для этого или предложите свой вариант.')
                res.addButton('кафе')
                res.addButton('пиццерия')
                res.addButton('кинотеатр')
                user.state = CHOOSE_PLACE
            elif city:
                res.addText('Знаю такой город, но это не он.')
                # координаты нашего места
                coord1 = maps.OUR_COORD
                # получение координат города, который ввел пользователь
                coord2 = maps.getCoord(city)
                # если город найден
                if coord1 and coord2:
                    # определение расстояние
                    distance = maps.lonlat_distance(coord1, coord2)
                    # перевод в километры
                    distance = int(distance / 1000)
                    res.addText(f'Вы ошиблись на {distance} км.')
                res.addText('Попробуй отгадать ещё раз.')
                res.addButton('покажи город')
            else:
                res.addText('Нет такого города. Попробуй отгадать ещё раз.')
                res.addButton('покажи город')

    else:
        res.addText('Вы вылезли через окно и неожиданно для вас вы оказываетесь на крыше пятиэтажки.')
        res.addText('Перед вами открывается вид на очень знакомый город.')
        res.addText('Попытайтесь его отгадать.')
        res.addButton('покажи город')
        user.state = GUESS_CITY


# поиск имени пользователя в запросе пользователя
def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name',
            # то возвращаем ее значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)


# поиск названия города в запросе пользователя
def get_city(req):
    # перебираем именованные сущности
    for entity in req['request']['nlu']['entities']:
        # если тип YANDEX.GEO, то пытаемся получить город(city), если нет, то возвращаем None
        if entity['type'] == 'YANDEX.GEO':
            # возвращаем None, если не нашли сущности с типом YANDEX.GEO
            return entity['value'].get('city', None)
