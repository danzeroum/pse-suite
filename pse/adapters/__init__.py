"""Adapters da PSE Suite para contratos externos.

Cada adapter converte um laudo-pse-1.0 em um formato de contrato
externo (ex.: evidence-bundle/v1). O adapter NÃO conhece CTRL-*,
ISO, risco, exceções, profiles ou decisões humanas — ele apenas
traduz o laudo para o formato de bundle, preservando proveniência
e sanitização.
"""
