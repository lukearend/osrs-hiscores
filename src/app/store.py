from dataclasses import dataclass

from dash import dcc


@dataclass
class SplitMenuState:
    split: dcc.Store


@dataclass
class BoxplotState:
    clusterid: dcc.Store
    nplayers: dcc.Store


@dataclass
class FrontendState:
    splitmenu: SplitMenuState
    boxplot: BoxplotState


@dataclass
class BackendState:
    currentsplit: dcc.Store
