class XmlHelper():
    def search(self, element, name):
        """Find a single element in the Xml with the tag = name"""
        return next((elem for elem in element.iter() if elem.tag == name), None)