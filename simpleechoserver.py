import socket
import socketserver
import selectors

import fcntl

import linuxfd

class handle_class(socketserver.BaseRequestHandler):
	"""handler untuk setiap koneksi"""

	def setup(self):
		self.request.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		self.counter = 0

		fcntl.fcntl(self.request.fileno(), fcntl.F_SETFL, socket.SOCK_NONBLOCK)
		fcntl.fcntl(self.request.fileno(), fcntl.F_SETFL, socket.SOCK_CLOEXEC)

		self.request.setblocking(False)

		# buat selectors
		self.sel = selectors.DefaultSelector()

		self.buffer_echo = b""

		# buat timerfd dengan linuxfd
		self.timer = linuxfd.timerfd(nonBlocking=True, closeOnExec=True)

	def finish(self):
		self.timer.close()
		self.request.close()

	def handle(self):

		# daftarkan rekues ke selector
		# hanya daftarkan event read
		self.sel.register(self.timer, selectors.EVENT_READ, self.callback_timer)
		self.sel.register(self.request, selectors.EVENT_READ, self.callback_socket)

		# start timer
		(timer_value, timer_interval) = self.timer.settime(value=2, interval=2)

		try:
			while (True):

				# select
				events = self.sel.select()
				for (key, mask) in events:
					callback = key.data
					(is_exit, data) = callback(mask)
					if (is_exit == True):
						return

		except (KeyboardInterrupt) as e:
			print("Interrupted")

	def callback_socket(self, mask):
		# self.rfile is a file-like object created by the handler;
		# we can now use e.g. readline() instead of raw recv() calls
		while (True):

			if ((mask & selectors.EVENT_READ) != 0):
				# handle bagian ini hanya jika kita read
				d = b""
				try:
					# baca socket
					d = self.request.recv(256)
				except (BlockingIOError) as e:
					# sudah tidak ada data yang bisa dibaca
					print("blocking read error")

					# hapus flag read dari mask (handler ini)
					# karena sudah tidak ada yang bisa di receive
					mask = mask & ~selectors.EVENT_READ

					# keluar dari while-loop jika tidak ada yang di write
					assert(not d)
					if (not self.buffer_echo):
						# buffer write kosong

						# kita tidak perlu tunggu event write
						self.remove_mask_event_write()

						# break while-loop
						break

					# kalau buffer_echo tidak kosong, maka biarkan handle write
					# yang mengambil keputusan

				# handle close
				if (not d):
					print("(%d) receive return 0" % (self.counter, ))

					self.counter = self.counter + 1
					return (True, None)

				# selalu print data yang berhasil di receive
				print("{} wrote:".format(self.client_address[0]))
				print(d)

				# masukkan d ke buffer buffer_echo
				self.buffer_echo = self.buffer_echo + d.upper()

			# tulis balik socket
			try:
				# kita tulis data berdasarkan buffer buffer_echo
				# kita tidak perlu cek flag write
				if (self.buffer_echo):
					# tulis ke socket
					write_len = self.request.send(self.buffer_echo)

					# buang data yang sudah ditulis
					self.buffer_echo = self.buffer_echo[write_len:]
					print("write_len: %d" % (write_len,))
				else:
					# hilangkan event write dari
					self.remove_mask_event_write()

					# keluar dari loop
					break

			except (BlockingIOError) as e:
				# write error
				print("blocking write error")

				try:
					write_len = e.characters_written
					if (write_len > 0):
						# potong buffer
						self.buffer_echo = self.buffer_echo[write_len:]

				except (AttributeError):
					pass

				# break jika tidak ada yang bisa dibaca
				if ((mask & selectors.EVENT_READ) == 0):
					if (not self.buffer_echo):
						self.remove_mask_event_write()

					break;

		return (False, None)

	def remove_mask_event_write(self):
		# kita tidak perlu tunggu event write
		# dapatkan SelectorKey
		key = self.sel.get_key(self.request)
		# set flag event di selectors menjadi wait for read
		# jika sebelumnya bukan wait for read
		if ((key.events & selectors.EVENT_WRITE) != 0):
			# hilangkan EVENT_WRITE
			self.sel.modify(self.request, key.events & ~selectors.EVENT_WRITE, data=key.data)

	def callback_timer(self, mask):
		assert(mask == selectors.EVENT_READ)
		while (True):
			try:
				last_expire = self.timer.read()
			except (BlockingIOError) as e:
			#except (OSError.EAGAIN) as e:
				# sudah tidak bisa baca lagi
				return (False, None) # tidak exit loop
			else:
				# increase counter
				self.counter = self.counter + 1

				print("timer expire (%d):" % (self.counter ,))

				# coba kirim data ke socketserver
				try:
					write_len = self.request.send(bytes("\ntimer expire (%d)\n" % (self.counter ,), encoding="utf-8"))
					print("mengirim timer ke klien")
				except (BlockingIOError) as e:
					print("BlockingIOError using timer to send to socket")
				except (Exception) as e:
					print("eksepsi lain")
					return (True, None) # exit loop

if __name__ == "__main__":

	#HOST = "localhost"
	HOST = ""
	PORT = 9999

	server = socketserver.ForkingTCPServer((HOST, PORT), handle_class)
	try:
		server.serve_forever()
	except (KeyboardInterrupt) as e:
		pass
	finally:
		server.shutdown()
