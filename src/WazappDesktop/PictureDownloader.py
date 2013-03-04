#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import threading
from .Events import Events
from .Contacts import Contacts

class PictureDownloader(Events):
    def __init__(self, connectionManager, contacts):
        super(PictureDownloader, self).__init__()
        self._pictureRequestsLock = threading.RLock()
        self._pictureRequests = {}
        self.signalsInterface = connectionManager.getSignalsInterface()
        self.methodsInterface = connectionManager.getMethodsInterface()
        for method, events in self.getEventBindings().iteritems():
            for event in events:
                self.signalsInterface.registerListener(event, method)

    def close(self):
        with self._pictureRequestsLock:
            for jid in self._pictureRequests.keys():
                self._removeRequest(jid)

    def _removeRequest(self, jid):
        with self._pictureRequestsLock:
            if jid in self._pictureRequests:
                request = self._pictureRequests[jid]
                if 'timer' in request:
                    try:
                        request['timer'].cancel()
                        request['timer'].join()
                    except:
                        pass
                if 'timeout' in request:
                    try:
                        request['timeout'].cancel()
                        request['timeout'].join()
                    except:
                        pass
                del self._pictureRequests[jid]

    @Events.bind('contact_gotProfilePictureId')
    def onProfilePictureId(self, jid, pictureId):
        Contacts.instance().setContactPictureId(jid, pictureId)
        pictureFilename = Contacts.instance().getContactPicture(jid)
        if not os.path.isfile(pictureFilename):
            #print 'onProfilePictureId(): queuing picture request for %s: %s' % (jid, pictureId)
            self._requestPicture(jid)

    def _requestPicture(self, jid):
        with self._pictureRequestsLock:
            if 'timeout' not in self._pictureRequests.get(jid, {}):
                delay = 0.2 * len(self._pictureRequests)
                #print 'onProfilePictureId(): requesting new picture for "%s" in %4.2fs' % (Contacts.instance().jid2name(jid), delay)
                request = self._pictureRequests.get(jid, {'numTimeouts': 0})
                request['timer'] = threading.Timer(delay, lambda: self.methodsInterface.call('picture_get', (jid,)))
                request['timeout'] = threading.Timer(delay + 2.0 + 0.5 * request['numTimeouts'], lambda: self._requestPictureTimeout(jid))
                self._pictureRequests[jid] = request
                request['timer'].start()
                request['timeout'].start()

    @Events.bind('contact_gotProfilePicture')
    def onProfilePicture(self, jid, filename):
        self._removeRequest(jid)
        #print 'onProfilePicture(): %s %s' % (jid, filename)
        pictureFilename = Contacts.instance().getContactPicture(jid)
        if pictureFilename is not None:
            #print 'onProfilePicture(): moving pic for "%s" pic to %s' % (Contacts.instance().jid2name(jid), pictureFilename)
            shutil.move(filename, pictureFilename)
        else:
            print 'onProfilePicture(): received picture for "%s" without requesting it' % (Contacts.instance().jid2name(jid))

    def _requestPictureTimeout(self, jid):
        with self._pictureRequestsLock:
            if jid in self._pictureRequests:
                numTimeouts = self._pictureRequests[jid]['numTimeouts'] + 1
                if numTimeouts >= 5:
                    print '_requestPictureTimeout(): pic request for "%s" timed out %d times, giving up' % (Contacts.instance().jid2name(jid), numTimeouts)
                    self._removeRequest(jid)
                    return
                self._pictureRequests[jid]['numTimeouts'] = numTimeouts
                del self._pictureRequests[jid]['timeout']
                # queue picture again
                self._requestPicture(jid)


