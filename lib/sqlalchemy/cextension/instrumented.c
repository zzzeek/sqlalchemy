/*
instrumented.c
Copyright (C) 2013 Claudio Freire klaussfreire@gmail.com

This module is part of SQLAlchemy and is released under
the MIT License: http://www.opensource.org/licenses/mit-license.php
*/

#include <Python.h>

#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
typedef Py_ssize_t (*lenfunc)(PyObject *);
#define PyInt_FromSsize_t(x) PyInt_FromLong(x)
typedef intargfunc ssizeargfunc;
#endif

#if PY_VERSION_HEX >= 0x03000000
#define PyString_InternFromString PyUnicode_InternFromString
#endif


PyObject *get_string = NULL;
PyObject *uget_string = NULL;

/* Forward decl, will need it */
static PyTypeObject InstrumentedGetterType;

/***********
 * Structs *
 ***********/

typedef struct {
    PyObject_HEAD

    /* Where to get instance_dict from */
    PyObject* globals;

    /* Name to which it was bound */
    PyObject* name;
    
    /* non-reference, just a pointer for identity comparison */
    void *cached_instance_dict;
    void *cached_impl;
    
    /* Only valid if cached_instance_dict != NULL and equal to global instance_dict */
    int cached_supports_population;
} InstrumentedGetter;

/**********************
 * InstrumentedGetter *
 **********************/

static int
InstrumentedGetter_init(InstrumentedGetter *self, PyObject *args, PyObject *kwds)
{
    PyObject *globals;

    if (!PyArg_UnpackTuple(args, "InstrumentedGetter", 1, 1,
                           &globals))
        return -1;

    Py_INCREF(globals);
    self->globals = globals;
    
    Py_INCREF(uget_string);
    self->name = uget_string;

    self->cached_instance_dict = NULL;
    self->cached_impl = NULL;

    return 0;
}

/* Bind to an object */
static PyObject *
InstrumentedGetter_descr_get(PyObject *func, PyObject *obj, PyObject *type)
{
    if (obj == Py_None)
        obj = NULL;
    
    return PyMethod_New((PyObject*)func, obj, type);
}

static PyObject *
InstrumentedGetter_get_name(InstrumentedGetter *op)
{
    Py_INCREF(op->name);
    return op->name;
}

static int
InstrumentedGetter_set_name(InstrumentedGetter *op, PyObject *value)
{
    PyObject *tmp;

    /* Not legal to del name or to set it to anything
     * other than a string object. */
    if (value == NULL || !PyString_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "__name__ must be set to a string object");
        return -1;
    }
    tmp = op->name;
    Py_INCREF(value);
    op->name = value;
    Py_DECREF(tmp);
    return 0;
}

static PyObject*
InstrumentedGetter_call(InstrumentedGetter *self, PyObject *args, PyObject *kwds)
{
    PyObject *me, *instance, *owner, *instance_dict, *basic_dict, *key, *impl, *rv, *x;
    int cacheable;
    int decself = 0;

    if (!PyArg_UnpackTuple(args, "InstrumentedGetter", 3, 3,
                           &me, &instance, &owner))
        return NULL;

    if (instance == NULL || instance == Py_None) {
        Py_INCREF(me);
        return me;
    }

    /* Check dict */
    instance_dict = PyMapping_GetItemString(self->globals, "instance_dict");
    if (instance_dict == NULL)
        return NULL;
    
    key = PyObject_GetAttrString(me, "key");
    if (key == NULL) {
        /* Um... bad... */
        Py_DECREF(instance_dict);
        return NULL;
    }

    basic_dict = PyObject_GetAttrString(instance, "__dict__");
    if (basic_dict == NULL) {
        /* No problem, we'll fall back to the generic implementation anyway */
        PyErr_Clear();
    }

    /* Check instance-specific cache */
    x = PyObject_GetAttrString(me, "__get__cache__");
    if (x != NULL && Py_TYPE(x) == &InstrumentedGetterType) {
        self = (InstrumentedGetter*)x;
        decself = 1;
    } else {
        /* Create one */
        PyErr_Clear();
        x = PyObject_CallFunctionObjArgs(
            (PyObject*)&InstrumentedGetterType, 
            self->globals,
            NULL );
        if (x != NULL) {
            ((InstrumentedGetter*)x)->name = self->name;
            Py_INCREF(self->name);
            if (PyObject_SetAttrString(me, "__get__cache__", x) != -1) {
                self = (InstrumentedGetter*)x;
                decself = 1;
            } else {
                Py_DECREF(x);
            }
        }
    }
    
    impl = NULL;
    
    if (   basic_dict != NULL
        && self->cached_instance_dict != NULL 
        && self->cached_instance_dict == instance_dict
        && self->cached_supports_population )
    {
        rv = PyObject_GetItem(basic_dict, key);
        if (rv == NULL) {
            /* OOps */
            PyErr_Clear();
            goto generic;
        }
    }
    else {
    generic:
        /* Disable caching until we can confirm cacheable behavior */
        impl = PyObject_GetAttrString(me, "impl");
        if (impl == NULL) {
            /* Um... bad... */
            rv = NULL;
            goto err;
        }
        
        if (impl != self->cached_impl) {
            if ((x = PyObject_GetAttrString(me, "_supports_population")) == NULL) {
                rv = NULL;
                goto err;
            }
            else {
                self->cached_impl = impl;
                self->cached_instance_dict = NULL; 
                self->cached_supports_population = PyObject_IsTrue(x);
                Py_DECREF(x);
            }
        }
        cacheable = 0;
        if (self->cached_supports_population) {
            x = PyObject_CallFunctionObjArgs(instance_dict, instance, NULL);
            if (x == NULL) {
                rv = NULL;
                goto err;
            }
            else {
                if (x == basic_dict) {
                    cacheable = 1;
                }
                Py_XDECREF(basic_dict);
                basic_dict = x;
            }

            rv = PyObject_GetItem(basic_dict, key);
            if (rv == NULL) {
                /* Ignore exception, will fall back to impl */
                PyErr_Clear();
            }
        }
        else {
            rv = NULL;
            x = PyObject_CallFunctionObjArgs(instance_dict, instance, NULL);
            if (x == NULL) {
                goto err;
            }
            else {
                Py_XDECREF(basic_dict);
                basic_dict = x;
            }
        }
        if (rv == NULL) {
            /* Fall back to impl */
            PyObject *instance_state;
            instance_state = PyMapping_GetItemString(self->globals, "instance_state");
            if (instance_state != NULL) {
                PyObject *state;
                state = PyObject_CallFunctionObjArgs(instance_state, instance, NULL);
                if (state != NULL) {
                    rv = PyObject_CallMethodObjArgs(impl, get_string, state, basic_dict, NULL);
                    Py_DECREF(state);
                }
                Py_DECREF(instance_state);
            }
            
        }
        if (rv != NULL && cacheable) {
            /* caching will work */
            self->cached_instance_dict = instance_dict;
        }
    }

err:
    if (decself) Py_DECREF(self);
    Py_DECREF(instance_dict);
    Py_XDECREF(impl);
    Py_DECREF(key);
    Py_XDECREF(basic_dict);
    return rv;
}

static void
InstrumentedGetter_dealloc(InstrumentedGetter *self)
{
    PyObject_GC_UnTrack((PyObject *)self);
    Py_XDECREF(self->globals);
    self->ob_type->tp_free((PyObject *)self);
}

static int
InstrumentedGetter_traverse(InstrumentedGetter *self, visitproc visit, void *arg)
{
    Py_VISIT(self->globals);
    return 0;
}

static int
InstrumentedGetter_clear(InstrumentedGetter *self)
{
    Py_CLEAR(self->globals);
    return 0;
}

static PyObject *
safe_InstrumentedGetter_reconstructor(PyObject *self, PyObject *args)
{
    PyObject *cls, *name;
    PyObject *attributes, *globals;
    InstrumentedGetter *obj;

    if (!PyArg_ParseTuple(args, "OO", &cls, &name))
        return NULL;

    attributes = PyImport_ImportModule("sqlalchemy.orm.attributes");
    if (attributes == NULL)
        return NULL;
    
    globals = PyModule_GetDict(attributes);
    if (globals == NULL)
        return NULL;

    obj = (InstrumentedGetter *)PyObject_CallMethod(cls, "__new__", "O", cls);
    if (obj == NULL)
        return NULL;

    Py_INCREF(globals);
    obj->globals = globals;
 
    Py_INCREF(name);
    obj->name = name;

    obj->cached_instance_dict = NULL;
    obj->cached_impl = NULL;

    return (PyObject *)obj;
}

static PyObject *
InstrumentedGetter_reduce(PyObject *self)
{
    PyObject *module, *reconstructor;

    module = PyImport_ImportModule("sqlalchemy.cinstrumented");
    if (module == NULL)
        return NULL;

    reconstructor = PyObject_GetAttrString(module, "safe_getter_reconstructor");
    Py_DECREF(module);
    if (reconstructor == NULL)
        return NULL;
    
    return Py_BuildValue("(N(NN))", reconstructor, Py_TYPE(self), ((InstrumentedGetter*)self)->name);
}

static PyGetSetDef InstrumentedGetter_getsetlist[] = {
    {"__name__", (getter)InstrumentedGetter_get_name, (setter)InstrumentedGetter_set_name},
    {NULL} /* Sentinel */
};

static PyMethodDef InstrumentedGetter_methods[] = {
    {"__reduce__",  (PyCFunction)InstrumentedGetter_reduce, METH_NOARGS,
     "Pickle support method."},
    {NULL} /* Sentinel */
};

static PyTypeObject InstrumentedGetterType = {
    PyObject_HEAD_INIT(NULL)
    0,                                  /* ob_size */
    "sqlalchemy.cinstrumented.InstrumentedGetter",          /* tp_name */
    sizeof(InstrumentedGetter),         /* tp_basicsize */
    0,                                  /* tp_itemsize */
    (destructor)InstrumentedGetter_dealloc,   /* tp_dealloc */
    0,                                  /* tp_print */
    0,                                  /* tp_getattr */
    0,                                  /* tp_setattr */
    0,                                  /* tp_compare */
    0,                                  /* tp_repr */
    0,                                  /* tp_as_number */
    0,                                  /* tp_as_sequence */
    0,                                  /* tp_as_mapping */
    0,                                  /* tp_hash */
    (ternaryfunc)InstrumentedGetter_call, /* tp_call */
    0,                                  /* tp_str */
    0,                                  /* tp_getattro */
    0,                                  /* tp_setattro */
    0,                                  /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,               /* tp_flags */
    "Stateful callable implementing an optimized instrumented attribute getter.",   /* tp_doc */
    (traverseproc)InstrumentedGetter_traverse, /* tp_traverse */
    (inquiry)InstrumentedGetter_clear,  /* tp_clear */
    0,                                  /* tp_richcompare */
    0,                                  /* tp_weaklistoffset */
    0,                                  /* tp_iter */
    0,                                  /* tp_iternext */
    InstrumentedGetter_methods,         /* tp_methods */
    0,                                  /* tp_members */
    InstrumentedGetter_getsetlist,      /* tp_getset */
    0,                                  /* tp_base */
    0,                                  /* tp_dict */
    InstrumentedGetter_descr_get,       /* tp_descr_get */
    0,                                  /* tp_descr_set */
    0,                                  /* tp_dictoffset */
    (initproc)InstrumentedGetter_init,  /* tp_init */
    0,                                  /* tp_alloc */
    0                                   /* tp_new */
};


#ifndef PyMODINIT_FUNC  /* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

static PyMethodDef module_methods[] = {
    {"safe_getter_reconstructor", safe_InstrumentedGetter_reconstructor, METH_VARARGS,
     "reconstruct a RowProxy instance from its pickled form."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyMODINIT_FUNC
initcinstrumented(void)
{
    PyObject *m;

    InstrumentedGetterType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&InstrumentedGetterType) < 0)
        return;

    m = Py_InitModule3("cinstrumented", module_methods,
                       "Module containing C versions of core ResultProxy classes.");
    if (m == NULL)
        return;

    get_string = PyString_InternFromString("get");
    uget_string = PyString_InternFromString("__get__");

    Py_INCREF(&InstrumentedGetterType);
    PyModule_AddObject(m, "InstrumentedGetter", (PyObject *)&InstrumentedGetterType);
}

