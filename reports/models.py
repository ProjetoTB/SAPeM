#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author:	Andressa Sivolella <andressasivolella@gmail.com>
# Date:		2011-12-04

from django.db import models
from django.contrib.auth.models import User

class Configuracao(models.Model):
	name            = models.CharField(max_length=200)
	user            = models.ForeignKey(User)
	creation_date   = models.DateTimeField(auto_now_add=True)
	settings        = models.TextField()
	class Meta:
		unique_together = ("name", "user")
