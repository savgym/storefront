from django.shortcuts import render
from store.models import Collection, Product


def say_hello(request):

    return render(request, 'hello.html', {'name': 'Savvas'})
