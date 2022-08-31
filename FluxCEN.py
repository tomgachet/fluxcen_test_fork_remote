# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FluxCEN
                                 A QGIS plugin
 Centralisation des flux WFS/WMS utilisés au CEN NA
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-03-23
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Romain MONTILLET
        email                : r.montillet@cen-na.org
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from PyQt5 import QtWidgets

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .FluxCEN_dialog import FluxCENDialog
import os.path, os, shutil
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import processing
import psycopg2
from PyQt5.QtXml import QDomDocument
import csv
import os
import io
import re
import random
import urllib
# Deal with SSL
import ssl
from urllib import request, parse
import json

ssl._create_default_https_context = ssl._create_unverified_context


class Flux:
    def __init__(self, t, c, nc, l, u, p):
        self.type = t
        self.category = c
        self.nom_commercial = nc
        self.layer = l
        self.url = u
        self.parameters = p


class FluxCEN:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'FluxCEN_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&FluxCEN')
        self.dlg = FluxCENDialog()

        self.plugin_path = os.path.dirname(__file__)

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

        self.dlg.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)
        self.dlg.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.dlg.comboBox.currentIndexChanged.connect(self.initialisation_flux)
        self.dlg.commandLinkButton.clicked.connect(self.selection_flux)
        self.dlg.tableWidget.itemDoubleClicked.connect(self.selection_flux)
        self.dlg.pushButton_2.clicked.connect(self.limite_flux)
        self.dlg.commandLinkButton_2.clicked.connect(self.suppression_flux)
        self.dlg.tableWidget_2.itemDoubleClicked.connect(self.suppression_flux)
        self.dlg.comboBox.addItem("toutes les catégories")
        self.dlg.commandLinkButton_3.clicked.connect(self.option_OSM)
        self.dlg.commandLinkButton_4.clicked.connect(self.option_google_maps)

        # iface.mapCanvas().extentsChanged.connect(self.test5)

        url_open = urllib.request.urlopen("https://raw.githubusercontent.com/CEN-Nouvelle-Aquitaine/fluxcen/main/flux.csv")
        colonnes_flux = csv.DictReader(io.TextIOWrapper(url_open, encoding='utf8'), delimiter=';')

        mots_cles = [row["categorie"] for row in colonnes_flux if row["categorie"]]
        categories = list(set(mots_cles))
        categories.sort()

        self.dlg.comboBox.addItems(categories)
        layout = QVBoxLayout()
        self.dlg.lineEdit.textChanged.connect(self.filtre_dynamique)
        layout.addWidget(self.dlg.lineEdit)
        self.dlg.lineEdit.mousePressEvent = self._mousePressEvent

        metadonnees_plugin = open(self.plugin_path + '/metadata.txt')
        infos_metadonnees = metadonnees_plugin.readlines()

        derniere_version = urllib.request.urlopen("https://sig.dsi-cen.org/qgis/downloads/last_version_fluxcen.txt")
        num_last_version = derniere_version.readlines()[0].decode("utf-8")

        print(num_last_version)
        print(infos_metadonnees[8])

        print(type(num_last_version))
        print(type(infos_metadonnees[8]))

        print(len(num_last_version))
        print(len(infos_metadonnees[8]))

        if infos_metadonnees[8] == num_last_version:
            iface.messageBar().pushMessage("Plugin à jour", "Votre version (%s) de FluxCEN est à jour ! :)" %infos_metadonnees[8], level=Qgis.Success)
        else:
            iface.messageBar().pushMessage("Information :", "Une nouvelle version de FluxCEN est disponible, veuillez mettre à jour le plugin !", level=Qgis.Info, duration=120)

    def _mousePressEvent(self, event):
        self.dlg.lineEdit.setText("")
        self.dlg.lineEdit.mousePressEvent = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('FluxCEN', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget
        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/FluxCEN/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'FluxCEN'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&FluxCEN'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def suppression_flux(self):
        self.dlg.tableWidget_2.removeRow(self.dlg.tableWidget_2.currentRow())

    def option_OSM(self):
        tms = 'type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmax=19&zmin=0'
        layer = QgsRasterLayer(tms, 'OSM', 'wms')

        if not QgsProject.instance().mapLayersByName("OSM"):
            QgsProject.instance().addMapLayer(layer)
        else:
            QMessageBox.question(iface.mainWindow(), u"Fond OSM déjà chargé !", "Le fond de carte OSM est déjà chargé", QMessageBox.Ok)

        OSM_layer = QgsProject.instance().mapLayersByName("OSM")[0]

        root = QgsProject.instance().layerTreeRoot()

        # Move Layer
        OSM_layer = root.findLayer(OSM_layer.id())
        myClone = OSM_layer.clone()
        parent = OSM_layer.parent()
        parent.insertChildNode(-1, myClone)
        parent.removeChildNode(OSM_layer)


    def option_google_maps(self):
        tms = 'type=xyz&zmin=0&zmax=20&url=https://mt1.google.com/vt/lyrs%3Ds%26x%3D{x}%26y%3D{y}%26z%3D{z}'
        layer = QgsRasterLayer(tms, 'Google Satelitte', 'wms')

        if not QgsProject.instance().mapLayersByName("Google Satelitte"):
            QgsProject.instance().addMapLayer(layer)
        else:
            QMessageBox.question(iface.mainWindow(), u"Fond Google Sat' déjà chargé !", "Le fond de carte Google Satelitte est déjà chargé", QMessageBox.Ok)

        google_layer = QgsProject.instance().mapLayersByName("Google Satelitte")[0]

        root = QgsProject.instance().layerTreeRoot()

        # Move Layer
        google_layer = root.findLayer(google_layer.id())
        myClone = google_layer.clone()
        parent = google_layer.parent()
        parent.insertChildNode(-1, myClone)
        parent.removeChildNode(google_layer)


    def initialisation_flux(self):

        def csv_import(url):
            url_open = urllib.request.urlopen(url)
            csvfile = csv.reader(io.TextIOWrapper(url_open, encoding='utf8'), delimiter=';')
            #on ne lit pas la première ligne correspondant aux noms des colonnes avec next()
            next(csvfile)
            return csvfile;

        data = []
        data2 = []
        model = QStandardItemModel()

        raw = csv_import(
            "https://raw.githubusercontent.com/CEN-Nouvelle-Aquitaine/fluxcen/main/flux.csv")

        for row in raw:
            data.append(row)
            data2.append(row)
            data = [k for k in data if self.dlg.comboBox.currentText() in k]
            data.sort()
            data2.sort()
            items = [
                QStandardItem(field)
                for field in row]

            model.appendRow(items)

        if self.dlg.comboBox.currentText() == 'toutes les catégories':
            # print(str(data2[0]))
            # del data2[0]
            # print(str(data2[0]))
            nb_row = len(data2)
            nb_col = len(data2[0])

            self.dlg.tableWidget.setRowCount(nb_row)
            self.dlg.tableWidget.setColumnCount(nb_col)
            for row in range(nb_row):
                for col in range(nb_col):
                    item = QTableWidgetItem(str(data2[row][col]))
                    self.dlg.tableWidget.setItem(row, col, item)
        else:
            nb_row = len(data)
            nb_col = len(data[0])
            self.dlg.tableWidget.setRowCount(nb_row)
            self.dlg.tableWidget.setColumnCount(nb_col)
            for row in range(nb_row):
                for col in range(nb_col):
                    item = QTableWidgetItem(str(data[row][col]))
                    self.dlg.tableWidget.setItem(row, col, item)

        self.dlg.tableWidget.setHorizontalHeaderLabels(["Service", "Catégorie", "Flux", "Nom technique", "Url d'accès", "Source", "Style"])

        self.dlg.tableWidget.setColumnWidth(0, 80)
        self.dlg.tableWidget.setColumnWidth(1, 0)
        self.dlg.tableWidget.setColumnWidth(2, 629)
        self.dlg.tableWidget.setColumnWidth(3, 0)
        self.dlg.tableWidget.setColumnWidth(4, 0)
        self.dlg.tableWidget.setColumnWidth(5, 100)
        self.dlg.tableWidget.setColumnWidth(6, 0)

        self.dlg.tableWidget.selectRow(0)

    def selection_flux(self):

        self.dlg.tableWidget_2.insertRow(0)

        for column in range(self.dlg.tableWidget.columnCount()):
            for a in [self.dlg.tableWidget.selectedItems()[column]]:
                cloned_item = a.clone()
                self.dlg.tableWidget_2.setHorizontalHeaderLabels(["Service", "Catégorie", "Flux sélectionné", "Nom technique", "Url d'accès", "Source", "Style"])
                self.dlg.tableWidget_2.setColumnCount(7)
                self.dlg.tableWidget_2.setItem(0,column,cloned_item)

        self.dlg.tableWidget_2.setColumnWidth(0,80)
        self.dlg.tableWidget_2.setColumnWidth(1,0)
        self.dlg.tableWidget_2.setColumnWidth(2,640)
        self.dlg.tableWidget_2.setColumnWidth(3,0)
        self.dlg.tableWidget_2.setColumnWidth(4,0)
        self.dlg.tableWidget_2.setColumnWidth(5,100)
        self.dlg.tableWidget_2.setColumnWidth(6, 0)

    def limite_flux(self):

        if self.dlg.tableWidget_2.rowCount() > 3:
            self.QMBquestion = QMessageBox.question(iface.mainWindow(), u"Attention !",
                                                    "Le nombre de flux à charger en une seule fois est limité à 3 pour des questions de performances. Souhaitez vous tout de même charger les " + str(
                                                        self.dlg.tableWidget_2.rowCount()) + " flux sélectionnés ? (risque de plantage de QGIS)",
                                                    QMessageBox.Yes | QMessageBox.No)
            if self.QMBquestion == QMessageBox.Yes:
                self.chargement_flux()

            if self.QMBquestion == QMessageBox.No:
                print("Annulation du chargement des couches")

        if self.dlg.tableWidget_2.rowCount() <= 3:
            self.chargement_flux()

    def chargement_flux(self):

        managerAU = QgsApplication.authManager()
        k = managerAU.availableAuthMethodConfigs().keys()
        # print( k )
        if len(list(k)) == 0:
            QMessageBox.question(iface.mainWindow(), u"Attention !", "Veuillez ajouter une entrée de configuration d'authentification dans QGIS pour accéder aux flux CEN-NA sécurisés par un mot de passe", QMessageBox.Ok)
        else:
            # for i in range(self.dlg.tableWidget_2.rowCount()):

            def REQUEST(type):
                switcher = {
                    'WFS': "GetFeature",
                    'WMS': "GetMap",
                    'WMS+Vecteur': "GetMap",
                    'WMS+Raster': "GetMap",
                    'WMTS': "GetMap",
                }
                return switcher.get(type, "nothing")


            def displayOnWindows(type, uri, name):

                if type == 'WFS':
                    vlayer = QgsVectorLayer(uri, name, "WFS")
                    # vlayer.setScaleBasedVisibility(True)
                    QgsProject.instance().addMapLayer(vlayer)
                    vlayer.loadNamedStyle(self.plugin_path + '/styles_couches/' + vlayer.name() + '.qml')
                    vlayer.triggerRepaint()

                    layers = QgsProject.instance().mapLayers()  # dictionary

                    # rowCount() This property holds the number of rows in the table
                    for row in range(self.dlg.tableWidget_2.rowCount()):
                        # item(row, 0) Returns the item for the given row and column if one has been set; otherwise returns nullptr.
                        _item = self.dlg.tableWidget_2.item(row, 2).text()
                        _legend = self.dlg.tableWidget_2.item(row, 6).text()
                        # print(_item)
                        # print(_legend)

                        for layer in layers.values():
                            if layer.name() == _item:
                                layer.loadNamedStyle(self.plugin_path + '/styles_couches/' + _legend + '.qml')


                elif type == 'WMS' or type == 'WMS Raster' or type == 'WMS Vecteur' or type == 'WMTS':
                    rlayer = QgsRasterLayer(uri, name, "WMS")
                    QgsProject.instance().addMapLayer(rlayer)
                else:
                    print("No WMS or WFS")

            p = []

            for row in range(0, self.dlg.tableWidget_2.rowCount()):
                    ## supression de la partie de l'url après le point d'interrogation
                    url = self.dlg.tableWidget_2.item(row,4).text().split("?", 1)[0]
                    try:
                        service = re.search('SERVICE=(.+?)&VERSION', self.dlg.tableWidget_2.item(row,4).text()).group(1)
                    except:
                        service = '1.0.0'
                    try:
                        version = re.search('VERSION=(.+?)&REQUEST', self.dlg.tableWidget_2.item(row,4).text()).group(1)
                    except:
                        version = '1.0.0'

                    if self.dlg.tableWidget_2.item(row,0).text() == 'WMS' or self.dlg.tableWidget_2.item(row,0).text() == 'WMS Raster':
                        if self.dlg.tableWidget_2.item(row,1).text() == 'drone' or self.dlg.tableWidget_2.item(row,1).text() == 'fonciercen':
                            a = Flux(
                                self.dlg.tableWidget_2.item(row,0).text(),
                                self.dlg.tableWidget_2.item(row,1).text(),
                                self.dlg.tableWidget_2.item(row,2).text(),
                                self.dlg.tableWidget_2.item(row,3).text(),
                                "url="+url,
                                {
                                    'service': self.dlg.tableWidget_2.item(row,0).text(),
                                    'version': version,
                                    'crs': "EPSG:2154",
                                    'format' : "image/png",
                                    'authcfg' : list(k)[0],
                                    'layers': self.dlg.tableWidget_2.item(row,3).text()+"&styles"
                                }
                            )

                        else:
                            a = Flux(
                                self.dlg.tableWidget_2.item(row,0).text(),
                                self.dlg.tableWidget_2.item(row,1).text(),
                                self.dlg.tableWidget_2.item(row,2).text(),
                                self.dlg.tableWidget_2.item(row,3).text(),
                                "url="+url,
                                {
                                    'service': self.dlg.tableWidget_2.item(row,0).text(),
                                    'version': version,
                                    'crs': "EPSG:2154",
                                    'format' : "image/png",
                                    'layers': self.dlg.tableWidget_2.item(row,3).text()+"&styles"
                                }
                            )
                        p.append(a)

                        uri = p[row].url + '&' + urllib.parse.unquote(urllib.parse.urlencode(p[row].parameters))
                        # print(uri)
                        # QgsMessageLog.logMessage(str(uri), "5sdf", level=Qgis.Info)
                        if not QgsProject.instance().mapLayersByName(p[row].nom_commercial):
                            displayOnWindows(p[row].type, uri, p[row].nom_commercial)
                        else:
                            print("Couche "+p[row].nom_commercial+" déjà chargée")
                    elif self.dlg.tableWidget_2.item(row, 0).text() == 'WMS Vecteur':
                        a = Flux(
                            self.dlg.tableWidget_2.item(row,0).text(),
                            self.dlg.tableWidget_2.item(row,1).text(),
                            self.dlg.tableWidget_2.item(row,2).text(),
                            self.dlg.tableWidget_2.item(row,3).text(),
                            "url="+url,
                            {
                                'service': self.dlg.tableWidget_2.item(row,0).text(),
                                'version': version,
                                'crs': "EPSG:4326",
                                'format' : "image/png",
                                'layers': self.dlg.tableWidget_2.item(row,3).text()+"&styles"
                            }
                        )

                        p.append(a)

                        uri = p[row].url + '&' + urllib.parse.unquote(urllib.parse.urlencode(p[row].parameters))
                        # print(uri)
                        # QgsMessageLog.logMessage(str(uri), "5sdf", level=Qgis.Info)
                        if not QgsProject.instance().mapLayersByName(p[row].nom_commercial):
                            displayOnWindows(p[row].type, uri, p[row].nom_commercial)
                        else:
                            print("Couche "+p[row].nom_commercial+" déjà chargée")
                    elif self.dlg.tableWidget_2.item(row,0).text() == 'WFS':
                        if self.dlg.tableWidget_2.item(row,1).text() == 'drone' or self.dlg.tableWidget_2.item(row,1).text() == 'fonciercen':
                            a = Flux(
                                self.dlg.tableWidget_2.item(row, 0).text(),
                                self.dlg.tableWidget_2.item(row, 1).text(),
                                self.dlg.tableWidget_2.item(row, 2).text(),
                                self.dlg.tableWidget_2.item(row, 3).text(),
                                url,
                                {
                                    'VERSION': version,
                                    'TYPENAME': self.dlg.tableWidget_2.item(row, 3).text(),
                                    'SRSNAME': "EPSG:4326",
                                    'authcfg': list(k)[0],
                                    'request': "GetFeature",

                                }
                            )
                        else:
                            a = Flux(
                            self.dlg.tableWidget_2.item(row, 0).text(),
                            self.dlg.tableWidget_2.item(row, 1).text(),
                            self.dlg.tableWidget_2.item(row, 2).text(),
                            self.dlg.tableWidget_2.item(row, 3).text(),
                                url,
                            {
                                'VERSION': version,
                                'TYPENAME': self.dlg.tableWidget_2.item(row, 3).text(),
                                'SRSNAME': "EPSG:4326",
                                'request': "GetFeature",

                            }
                        )

                        p.append(a)

                        uri = p[row].url + '?' + urllib.parse.unquote(urllib.parse.urlencode(p[row].parameters))
                        # print(uri)

                        if not QgsProject.instance().mapLayersByName(p[row].nom_commercial):
                            displayOnWindows(p[row].type, uri, p[row].nom_commercial)
                        else:
                            print("Couche "+p[row].nom_commercial+" déjà chargée")


                    else:
                        print("Les flux WMTS et autres ne sont pas encore gérés par le plugin")



    def filtre_dynamique(self, filter_text):

        for i in range(self.dlg.tableWidget.rowCount()):
            for j in range(self.dlg.tableWidget.columnCount()):
                item = self.dlg.tableWidget.item(i, j)
                match = filter_text.lower() not in item.text().lower()
                self.dlg.tableWidget.setRowHidden(i, match)
                if not match:
                    break






# from owslib.wfs import WebFeatureService
# import csv

# wfs = WebFeatureService(url='https://opendata.cen-nouvelle-aquitaine.org/geoserver/agriculture/wfs')
# agriculture = list(wfs.contents)
# with open('C:/Users/Romain/Desktop/test.csv', "a+", encoding="ISO-8859-1", newline='') as f:
#     writer = csv.writer(f)
#     for row in agriculture:
#         writer.writerow(row.split())
#
# from owslib.wms import WebMapService
# wms = WebMapService('https://opendata.cen-nouvelle-aquitaine.org/geoserver/fond_carto/wms')
# fonds_carto = list(wms.contents)
# with open('C:/Users/Romain/Desktop/test.csv', "a+", encoding="ISO-8859-1", newline='') as f:
#     writer = csv.writer(f)
#     for row in fonds_carto:
#         writer.writerow(row.split())
#
# import csv
#
# fluxWMS = ['AGG_TMM', '16-014_Brandes_de_Soyaux_2020-05', '17IMERIS_Bois-Charles_Vallée-du-Larry_2022_01', '17IMERIS_Grand-Champ_2022-01', '19PTOR_MNS_filtre_futurs_travaux_2021-10_L93', '19PTOR_MNS_filtre_travaux_realises_2021-10_L93', '19PTOR_ortho_2021-10_L93', '23CELI_marais_du_chancelier_2022_03_24', '23CLAM_Rocher_de_Clamouzat_2020-11', '23DIAB_lande_du_pont_du_diable_nord_2021-10_L93', '23DIAB_lande_du_pont_du_diable_sud_2021-10_L93', '23LAND_RNN_etang_des_landes_2020-08_L93', '33_Lagune-108-2021-08', '79BLVI_Blanchère-de-Viennay_2021-10', '79VGAT_Vallée-du-Gâteau_Pressigny_2020-02', '79VGAT_Vallée-du-Gâteau_Pressigny_2021-10', '86-001_TMM_CA-CD_2020-07', '86-500_Clain-sud_Etang-du-Pin', '86_AT_Chalandray_2021-10', '87CREN_siege_saint_gence_2021-09', '87GRLA_grandes_landes_2021-09-24', '87SANA_sanadie_2021-09-24', 'a_16_030_Prairies_de_Vouharte_2019_09', 'a_17_474_Estauaire_de_la_Gironde_Les_Pr_s_de_la_Rouille_2019_08', 'a_17_474_Estauaire_de_la_Gironde_Moulin_Rompu_2019_08', 'a_17_474_Estuaire_de_la_Gironde_Zone_Humide_de_la_Motte_Ronde_2021_04', 'a_17_IMERIS_Carriere_du_Planton_2021_08_12', 'a_17_LGV_Ragouillis_2021_08_12', 'a_33_Lagune_058_2021_08', 'a_33_Lagune_070_2021_08', 'a_33_Lagune_094_2021_08', 'a_33_Lagune_162_2021_08', 'a_33_Lagune_165_2021_08', 'a_33_Lagunes_207_208_209_2021_08', 'a_79_001_Clussais_la_Pommeraie_2020_11', 'a_79_008_Landes_de_L_Hopiteau_2019_09', 'a_79_020_Bessines_1_avant_travaux_2019_10', 'a_79_020_Bessines_2_pendant_travaux_2019_11', 'a_79_020_Bessines_3_apres_travaux_2020_12', 'a_79_044_Carriere_des_Landes_2020_09', 'a_79_AT_Vernoux_en_Gatine_2020_09', 'a_79_Sources_de_la_Sevre_Niortaise_Pierre_levee_2020_09', 'a_86_001_TMM_AA_2020_06', 'a_86_001_TMM_AB_2020_06', 'a_86_001_TMM_AC_2020_06', 'a_86_001_TMM_AD_2020_06', 'a_86_001_TMM_AE_2020_06', 'a_86_001_TMM_AF_2020_06', 'a_86_001_TMM_AG_2020_07', 'a_86_001_TMM_BA_2020_06', 'a_86_001_TMM_BB_2020_06', 'a_86_001_TMM_BC_2020_06', 'a_86_001_TMM_BD_2020_06', 'a_86_001_TMM_BE_2020_07', 'a_86_001_TMM_BF_2021_06', 'a_86_001_TMM_CB_2020_07', 'a_86_001_TMM_CC_2020_07', 'a_86_001_TMM_CC_2021_06', 'a_86_001_TMM_CD_2021_06', 'a_86_001_TMM_CE_2020_07', 'a_86_001_TMM_CF_2020_09', 'a_86_001_TMM_DA_2020_07', 'a_86_001_TMM_DB_2020_09', 'a_86_001_TMM_DC_2021_06', 'a_86_001_TMM_EA_2020_06', 'a_86_001_TMM_EB_2020_06', 'a_86_001_TMM_EC_2020_06', 'a_86_001_TMM_FA_2020_06', 'a_86_001_TMM_FB_2020_07', 'a_86_001_TMM_FC_2020_07', 'a_86_001_TMM_FC_2021_06', 'a_86_001_TMM_HA_2020_09', 'a_86_001_TMM_IA_2020_06', 'a_86_001_TMM_IB_2020_06', 'a_86_001_TMM_IC_2020_06', 'a_86_001_TMM_JA_2020_07', 'a_86_001_TMM_JB_2020_07', 'a_86_001_TMM_JC_2020_07', 'a_86_001_TMM_JE_2020_07', 'a_86_001_TMM_KA_2020_07', 'a_86_001_TMM_KB_2020_07', 'a_86_003_Falunieres_de_Moulin_Pochas_2019_09', 'a_86_006_Landes_et_pelouses_de_Lussac_Sillars_2019_08', 'a_86_011_Landes_de_Sainte_Marie_2019_09', 'a_86_025_Marais_des_Ragouillis_2020_11', 'a_86_025_Marais_des_Ragouillis_2021_02', 'a_86_026_Etangs_Baro_2019_09', 'a_86_029_Vallee_de_la_Longere_2019_09', 'a_86_037_Tourbiere_des_Regeasses_2021_06', 'a_86_038_Vallees_de_la_Vienne_et_du_Clain_Persac_2019_09', 'a_86_038_Vallees_de_la_Vienne_et_du_Clain_Persac_2020_12', 'a_86_052_Fontaine_le_Comte_nord_2020_11', 'a_86_052_Fontaine_le_Comte_sud_2020_11', 'a_86_054_Vallee_de_la_Vonne_2020_11', 'a_86_058_Carriere_de_Puy_Herve_2021_02_09', 'a_86_058_Carriere_de_Puy_Herve_2021_02_25', 'a_86_060_Bocage_de_la_Geoffronniere_2020_11', 'a_86_Le_Cormier_2021_05']
#
# with open('C:/Users/Romain/Desktop/test.csv', "a+", encoding="ISO-8859-1", newline='') as f:
#     writer = csv.writer(f)
#     for row in fluxWMS:
#         writer.writerow(row.split())

#