
#ifndef CA_USERTOOLS_H
#define CA_USERTOOLS_H

#include "thread.h"
#include "net.h"
#include "token.h"
#include "place.h"

#include <vector>
#include <string>
#include <exception>
#include <stdexcept>


namespace ca {

//My own assert exception
class AssertException: public std::runtime_error{
    private:
        const char* assertMessage;
        //Rovnalo nebo nerovnalo se to?
        bool isOk;
    public:
        AssertException(const char* msg, bool ok) : std::runtime_error(""){
            assertMessage = msg;
            isOk = ok;
        }
        ~AssertException() throw() {}
        virtual const char * what () const throw ()
        {
            return assertMessage;
        }
};

class Context {
	public:
		Context(ThreadBase *thread, NetBase *net) : thread(thread), net(net) {}

		void quit() {
			thread->quit_all();
		}

		int process_id() const {
			return thread->get_process_id();
		}

		int process_count() const {
			return thread->get_process_count();
		}

		void trace_value(const std::string &str) {
			TraceLog *tracelog = thread->get_tracelog();
			if (tracelog) {
				tracelog->trace_value(str);
			}
		}
		void trace(const int value) {
			TraceLog *tracelog = thread->get_tracelog();
			if (tracelog) {
				tracelog->trace_value(value);
			}
		}
		void trace(const double value) {
			TraceLog *tracelog = thread->get_tracelog();
			if (tracelog) {
				tracelog->trace_value(value);
			}
		}


	protected:
		ThreadBase *thread;
		NetBase *net;
};

	std::vector<int> range(int from, int upto);
	inline std::vector<int> all_processes(Context &ctx) {
		return range(0, ctx.process_count());
	}

    template <typename T>
    void store(Place<T> &place,
               const std::string &path,
               const std::string &mode,
               const bool all=false) {

        FILE *f = fopen(path.c_str(), mode.c_str());
        if (f == NULL) {
            perror("Unable to open for storing place data.\n");
            exit(-1);
        }

        Token<T> *t = place.begin();
        do {
            if (t == NULL) {
                break;
            }
            Packer packer;
            ca::pack(packer, t->value);
            size_t size = packer.get_size();
            fwrite(&size, sizeof(size_t), 1, f);
            fwrite(packer.get_buffer(), 1, size, f);

            t = place.next(t);
        } while (all); // bulk edge

        fclose(f);
    }
//vyhodit vyjimku vlastni
    template<typename T>
    void assertEquals(const std::string &message, const T expected, const T actual) {
        std::stringstream msg;
        if(expected != actual) {
            msg << "ErrorCode: 0x000;" << message << ";" << expected << ";" << actual << ";";
            throw AssertException(msg.str().c_str(), false);//vyjimka!
        }
        else {
            msg << "ErrorCode: 0x001;" << message << ";" << expected << ";" << actual << ";";
             throw AssertException(msg.str().c_str(), true);//vyjimka!
        }
    }

    //Vyhodí pouze výjimku
    void assertFail(const std::string &message) {
        throw AssertException(message.c_str(), false);
    }

    //Podle porovnavaci funkce
    template<typename T>
    void assert(const std::string &message, bool (* func)(T, T), T obj1, T obj2) {
        std::stringstream msg;
        if((* func)(obj1, obj2)) {
            msg << "ErrorCode: 0x000;" << message << ";" << obj1 << ";" << obj2 << ";";
            throw AssertException(msg.str().c_str(), true);
        } else {
            msg << "ErrorCode: 0x000;" << message << ";" << obj1 << ";" << obj2 << ";";
            throw AssertException(msg.str().c_str(), false);
        }
    }

    template<typename T>
    void load(const std::string &path, TokenList<T> &token_list) {

       FILE *f = fopen(path.c_str(), "rb");
       if (f == NULL) {
           perror("Unable to open file with place data.\n");
           exit(-1);
       }

       size_t pos = 0;

       // get size of file
       size_t f_size;
       fseek(f, 0, SEEK_END);
       f_size = ftell(f);
       rewind(f);

       size_t n;
       size_t size;
       while (pos < f_size) { // unpack stored data data
           n = fread(&size, sizeof(size_t), 1, f);
           if (n != 1) {
               perror("Place initialization from file; reading data size.\n");
               exit(-1);
           }
           pos += n * sizeof(size_t);

           char *buffer = (char *) malloc(size);
           n = fread(buffer, 1, size, f);
           if (n != size) {
               perror("Place initialization from file; reading data.\n");
               exit(-1);
           }
           pos += n;

           T value;
           Unpacker unpacker(buffer);
           ca::unpack(unpacker, value);
           token_list.add(value); // add value to place

           free(buffer);
       }
       fclose(f);
   }

}

#endif // CA_USERTOOLS_H
