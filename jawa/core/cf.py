try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from struct import unpack
import jawa.core.constants as const
import jawa.core.fields as fields
import jawa.core.methods as methods
import jawa.core.attributes as attributes


class ClassFile(object):
    """
    Creates a new JVM ClassFile, optionally loading the JVM class at `io`,
    where `io` is a file-like object providing `read()` or a file-system path.
    """
    def __init__(self, io=None, context=None):
        self._constants = const.ConstantPool()
        self._fields = fields.FieldTable(self)
        self._methods = methods.MethodTable(self)
        self._attributes = attributes.AttributeTable(self)
        self._interfaces = []
        self._super = None
        self._this = None
        self._version = (0, 0)
        self._context = context

        if io and isinstance(io, basestring):
            # The paths returned by EditableZipFile's query methods are
            # strings, but also support an origin-aware read() method.
            if hasattr(io, 'read'):
                fin = StringIO(io.read())
                self._load_from_io(fin)
                fin.close()
            else:
                # ... or we just got a normal filesystem path.
                fin = open(io, 'rb')
                self._load_from_io(fin)
                fin.close()
        elif io:
            self._load_from_io(io)
        else:
            # We need to construct a default name and superclass.
            self.build_this("HelloWorld")
            self.build_superclass("java/lang/Object")

    def build_this(self, name):
        """
        A helper to set the class of this ``ClassFile``. It generates the
        required ``Constants*`` and inserts them into the pool.
        """
        _, self._this = self.constants.build_class(name)

    def build_superclass(self, name):
        """
        A helper to set the superclass of this ``ClassFile``. It generates the
        required ``Constants*`` and inserts them into the pool.
        """
        _, self._super = self.constants.build_class(name)

    @property
    def this(self):
        """
        Returns the :class:`~jawa.core.constants.ConstantClass` for this
        ``ClassFile``.
        """
        return self._this

    @this.setter
    def this(self, value):
        if not isinstance(value, const.ConstantClass):
            raise TypeError('this must be a ConstantClass.')
        self._this = value

    @property
    def superclass(self):
        """
        Returns the :class:`~jawa.core.constants.ConstantClass` for the
        superclass of this ``ClassFile``.
        """
        return self._super

    @superclass.setter
    def superclass(self, value):
        if not isinstance(value, const.ConstantClass):
            raise TypeError('superclass must be a ConstantClass.')
        self._super = value

    def get_superclass(self, context=None):
        """
        Lookup and return a :class:`~jawa.core.cf.ClassFile` for this class's
        superclass using the currently active context. If `context` is provided
        it overrides the active context. If the superclass cannot be found,
        ``None`` is returned.
        """
        context = context or self.context
        if self.superclass.name == 'java/lang/Object':
            return None
        return context.find_class(self.superclass.name)

    @property
    def interfaces(self):
        """
        Returns a list of :class:`~jawa.core.constants.ConstantClass`
        objects, one for each direct superinterface of this class or
        interface.
        """
        return self._interfaces

    @classmethod
    def from_str(cls, data, context=None):
        """
        Returns a new :class:`~jawa.core.cf.ClassFile` from a string buffer.

        >>> from jawa.util.jf import JarFile
        >>> from jawa.core.cf import ClassFile
        >>> with JarFile(sys.argv[1]) as jf:
        ...    for path in jf.namelist():
        ...        cf = ClassFile.from_str(jf.read(path))
        """
        sio = StringIO(data)
        tmp = cls(io=sio, context=context)
        sio.close()
        return tmp

    @property
    def version(self):
        """
        The class file version as a tuple in the form (major, minor).
        """
        return self._version

    @property
    def constants(self):
        """
        Returns the :class:`~jawa.core.constants.ConstantPool` for this
        ``ClassFile``.
        """
        return self._constants

    @property
    def fields(self):
        """
        Returns the :class:`~jawa.core.fields.FieldTable` for this
        ``ClassFile``.
        """
        return self._fields

    @property
    def methods(self):
        """
        Returns the :class:`~jawa.core.methods.MethodTable` for this
        ``ClassFile``.
        """
        return self._methods

    @property
    def attributes(self):
        """
        Returns the :class:`~jawa.core.attributes.AttributeTable` for this
        ``ClassFile``.
        """
        return self._attributes

    @property
    def context(self):
        """
        The currently active :class:`~jawa.core.context.Context` for
        this ``ClassFile``.
        """
        return self._context

    @version.setter
    def version(self, value):
        self._version = value

    def _load_from_io(self, io):
        """
        Parses a raw `ClassFile` given a file-like object `io` providing
        a blocking `read()`.
        """
        if unpack('>I', io.read(4))[0] != 0xCAFEBABE:
            raise IOError('Not a ClassFile!')

        minv, maxv = unpack('>HH', io.read(4))
        self._version = (maxv, minv)
        self.constants._load_from_io(io)

        flags, this, super_, if_count = unpack('>HHHH', io.read(8))
        self.access_flags = flags
        self._this = self.constants[this]
        self._super = self.constants[super_]

        interfaces = unpack('>%sH' % if_count, io.read(if_count * 2))
        interfaces = [self.constants.get(i) for i in interfaces]
        self._interfaces = interfaces

        self.fields._load_from_io(io)
        self.methods._load_from_io(io)
        self.attributes._load_from_io(io)
