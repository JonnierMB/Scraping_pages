class Property:
    def __init__(self, title, address, price, squaremeter, bedrooms, toilets, parking, url, img,description, source):
        self.title=title
        self.address=address
        self.price=price
        self.squaremeter=squaremeter
        self.bedrooms=bedrooms
        self.toilets=toilets
        self.parking=parking
        self.url=url
        self.img = img
        self.description = description
        self.source=source

    def to_dict(self):
        return{
            "title": self.title,
            "address": self.address,
            "price": self.price,
            "squaremeter": self.squaremeter,
            "bedrooms": self.bedrooms,
            "toilets": self.toilets,
            "parking":self.parking,
            "url": self.url,
            "img": self.img,
            "description": self.description,
            "source":self.source
        }