class Line:
    """
    This class models a bus line.
    """

    def __init__(self, code: str, name: str, url: str):
        """Constructor

        :param code: code of the line
        :param name: canonical name of the line
        :param url: url to the pdf file of the timetable
        """
        self.code = code
        self.name = name
        self.url = url
        self.cities = list()
        self.file_hash = None

        # list of ids of chats subscribed to changes in this line
        self.user_subscriptions = list()

    @staticmethod
    def from_dict(source: dict):
        line = Line(source['code'], source['name'], source['timetable_url'])
        line.cities = list(source['cities'])
        line.file_hash = source['file_hash']
        if 'user_subscriptions' in source:
            line.user_subscriptions = list(source['user_subscriptions'])
        return line

    def to_dict(self):
        return {
            u'code': self.code,
            u'name': self.name,
            u'timetable_url': self.url,
            u'cities': list(self.cities),
            u'file_hash': self.file_hash,
            u'user_subscriptions': list(self.user_subscriptions),
        }

    def __eq__(self, other):
        """
        Two instances of Line are equals if their codes are equals.

        :return: true if the two instances are equal
        """
        return isinstance(other, Line) and self.code == other.code

    def __hash__(self):
        return hash(self.code)

    def __repr__(self):
        return f"Line({self.code})"
