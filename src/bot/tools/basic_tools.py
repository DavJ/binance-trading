def get_java_name(text, title_first=True):
    # saving first and rest using split()
    init, *temp = text.split('_')
    if title_first:
        return ''.join([init.title(), *map(str.title, temp)])
    else:
        return ''.join([init.lower(), *map(str.title, temp)])


#print(get_java_name(text='test_string'))
